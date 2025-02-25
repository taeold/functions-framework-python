# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import functools
import io
import json
import logging
import random
import re
import string
import sys
import contextvars
import asyncio
from typing import Dict, Optional, Any, Union, Callable

# Import Flask and related modules conditionally
# We use a consistent import pattern with None values when imports fail
# This makes it clearer when checking if modules are available elsewhere
flask = None
LocalProxy = None
try:
    import flask
    from werkzeug.local import LocalProxy
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

_EXECUTION_ID_LENGTH = 12
_EXECUTION_ID_CHARSET = string.digits + string.ascii_letters
_LOGGING_API_LABELS_FIELD = "logging.googleapis.com/labels"
_LOGGING_API_SPAN_ID_FIELD = "logging.googleapis.com/spanId"
_TRACE_CONTEXT_REGEX_PATTERN = re.compile(
    r"^(?P<trace_id>[\w\d]+)/(?P<span_id>\d+);o=(?P<options>[01])$"
)
EXECUTION_ID_REQUEST_HEADER = "Function-Execution-Id"
TRACE_CONTEXT_REQUEST_HEADER = "X-Cloud-Trace-Context"

logger = logging.getLogger(__name__)

# Context variable for storing execution context in ASGI apps
execution_context_var = contextvars.ContextVar("execution_context", default=None)


class ExecutionContext:
    def __init__(self, execution_id=None, span_id=None):
        self.execution_id = execution_id
        self.span_id = span_id


def _get_current_context() -> Optional[ExecutionContext]:
    """Get the current execution context.
    
    Returns execution context from the appropriate storage mechanism:
    - For ASGI apps: retrieves from the contextvars-based storage
    - For WSGI (Flask) apps: retrieves from flask.g if in request context
    
    Returns:
        The current ExecutionContext object or None if not in a request.
    """
    # First check the context variable for ASGI
    # This works for both ASGI and WSGI since we always set it in both
    context = execution_context_var.get()
    if context is not None:
        return context
    
    # Legacy Flask-only approach as fallback
    if FLASK_AVAILABLE and flask is not None:
        if flask.has_request_context() and hasattr(flask.g, "execution_id_context"):
            return flask.g.execution_id_context
    
    return None


def _set_current_context(context: ExecutionContext) -> Optional[contextvars.Token]:
    """Set the current execution context.
    
    Sets execution context in the appropriate storage mechanism:
    - For all apps: sets in contextvars-based storage
    - For WSGI (Flask) apps: also sets in flask.g if in request context
    
    Args:
        context: The ExecutionContext to store
        
    Returns:
        Token for resetting context if using contextvars, or None
    """
    # Always set the context variable - works for both ASGI and WSGI
    token = execution_context_var.set(context)
    
    # Also set in Flask if available and in request context (legacy approach)
    if FLASK_AVAILABLE and flask is not None:
        if flask.has_request_context():
            flask.g.execution_id_context = context
            
    return token


def _generate_execution_id() -> str:
    """Generate a random execution ID."""
    return "".join(
        _EXECUTION_ID_CHARSET[random.randrange(len(_EXECUTION_ID_CHARSET))]
        for _ in range(_EXECUTION_ID_LENGTH)
    )


# WSGI middleware to add execution id to request header if one does not already exist
class WsgiMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        execution_id = (
            environ.get("HTTP_FUNCTION_EXECUTION_ID") or _generate_execution_id()
        )
        environ["HTTP_FUNCTION_EXECUTION_ID"] = execution_id
        return self.wsgi_app(environ, start_response)


# ASGI middleware to add execution id to request
class AsgiMiddleware:
    """ASGI middleware that ensures an execution ID for each request.
    
    This middleware:
    1. Checks if the request has an execution ID header
    2. If not, generates a new execution ID and adds it to the request headers
    3. Passes the request to the next middleware or application
    
    The execution ID can then be accessed by the application code
    through `_get_current_context()`.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only process HTTP requests, pass through other types
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        
        # Find execution_id in headers
        execution_id = None
        header_name_bytes = EXECUTION_ID_REQUEST_HEADER.lower().encode()
        
        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == header_name_bytes:
                # Header exists, get its value
                execution_id = header_value.decode("utf-8", errors="replace")
                break
        
        # If no execution ID found, generate one and add it to headers
        if not execution_id:
            execution_id = _generate_execution_id()
            
            # Create a new headers list with our execution ID added
            headers = list(scope.get("headers", []))
            headers.append((header_name_bytes, execution_id.encode("utf-8")))
            scope["headers"] = headers
        
        # Pass the modified scope to the next middleware/application
        return await self.app(scope, receive, send)


# Sets execution id and span id for the Flask request
def set_execution_context(request, enable_id_logging=False):
    if enable_id_logging:
        stdout_redirect = contextlib.redirect_stdout(
            LoggingHandlerAddExecutionId(sys.stdout)
        )
        stderr_redirect = contextlib.redirect_stderr(
            LoggingHandlerAddExecutionId(sys.stderr)
        )
    else:
        stdout_redirect = contextlib.nullcontext()
        stderr_redirect = contextlib.nullcontext()

    def decorator(view_function):
        @functools.wraps(view_function)
        def wrapper(*args, **kwargs):
            trace_context = re.match(
                _TRACE_CONTEXT_REGEX_PATTERN,
                request.headers.get(TRACE_CONTEXT_REQUEST_HEADER, ""),
            )
            execution_id = request.headers.get(EXECUTION_ID_REQUEST_HEADER)
            span_id = trace_context.group("span_id") if trace_context else None
            _set_current_context(ExecutionContext(execution_id, span_id))

            with stderr_redirect, stdout_redirect:
                return view_function(*args, **kwargs)

        return wrapper

    return decorator


# Sets execution id and span id for ASGI (Starlette) requests
def set_asgi_execution_context(enable_id_logging=False):
    """ASGI-compatible execution context setter for Starlette requests.
    
    This decorator:
    1. Extracts execution ID and span ID from request headers
    2. Sets them in the context variables storage
    3. Runs the handler function
    4. Resets the context afterwards
    
    Args:
        enable_id_logging: Whether to configure logging to include execution IDs
        
    Returns:
        A decorator function that wraps the handler function
    """
    # Set up output redirection once, not on every request
    if enable_id_logging:
        stdout_handler = LoggingHandlerAddExecutionId(sys.stdout)
        stderr_handler = LoggingHandlerAddExecutionId(sys.stderr)
        stdout_redirect = contextlib.redirect_stdout(stdout_handler)
        stderr_redirect = contextlib.redirect_stderr(stderr_handler)
    else:
        stdout_redirect = contextlib.nullcontext()
        stderr_redirect = contextlib.nullcontext()

    # The actual decorator function
    def decorator(func):
        # Extract common header processing code to avoid duplication
        def _extract_context_from_headers(request):
            # Get trace context if available
            trace_context_header = request.headers.get(TRACE_CONTEXT_REQUEST_HEADER, "")
            trace_context = re.match(_TRACE_CONTEXT_REGEX_PATTERN, trace_context_header)
            span_id = trace_context.group("span_id") if trace_context else None
            
            # Get execution ID from headers or create one
            execution_id = request.headers.get(EXECUTION_ID_REQUEST_HEADER)
            if not execution_id:
                execution_id = _generate_execution_id()
                
            return ExecutionContext(execution_id, span_id)
        
        # For async functions (coroutines)
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(request, *args, **kwargs):
                # Extract and set context
                context = _extract_context_from_headers(request)
                token = _set_current_context(context)
                
                # Execute the function with context and clean up after
                try:
                    with stderr_redirect, stdout_redirect:
                        return await func(request, *args, **kwargs)
                finally:
                    if token:
                        execution_context_var.reset(token)
            
            return async_wrapper
        
        # For synchronous functions
        else:
            @functools.wraps(func)
            def sync_wrapper(request, *args, **kwargs):
                # Extract and set context
                context = _extract_context_from_headers(request)
                token = _set_current_context(context)
                
                # Execute the function with context and clean up after
                try:
                    with stderr_redirect, stdout_redirect:
                        return func(request, *args, **kwargs)
                finally:
                    if token:
                        execution_context_var.reset(token)
            
            return sync_wrapper
    
    return decorator


# Only define the LocalProxy if Flask is available
if FLASK_AVAILABLE:
    @LocalProxy
    def logging_stream():
        return LoggingHandlerAddExecutionId(stream=flask.logging.wsgi_errors_stream)
else:
    logging_stream = None


class LoggingHandlerAddExecutionId(io.TextIOWrapper):
    def __new__(cls, stream=sys.stdout):
        if isinstance(stream, LoggingHandlerAddExecutionId):
            return stream
        else:
            return super(LoggingHandlerAddExecutionId, cls).__new__(cls)

    def __init__(self, stream=sys.stdout):
        io.TextIOWrapper.__init__(self, io.StringIO())
        self.stream = stream

    def write(self, contents):
        if contents == "\n":
            return
        current_context = _get_current_context()
        if current_context is None:
            self.stream.write(contents + "\n")
            self.stream.flush()
            return
        try:
            execution_id = current_context.execution_id
            span_id = current_context.span_id
            payload = json.loads(contents)
            if not isinstance(payload, dict):
                payload = {"message": contents}
        except json.JSONDecodeError:
            if len(contents) > 0 and contents[-1] == "\n":
                contents = contents[:-1]
            payload = {"message": contents}
        if execution_id:
            payload[_LOGGING_API_LABELS_FIELD] = payload.get(
                _LOGGING_API_LABELS_FIELD, {}
            )
            payload[_LOGGING_API_LABELS_FIELD]["execution_id"] = execution_id
        if span_id:
            payload[_LOGGING_API_SPAN_ID_FIELD] = span_id
        self.stream.write(json.dumps(payload))
        self.stream.write("\n")
        self.stream.flush()
