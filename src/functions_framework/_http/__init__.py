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

import os
from functions_framework._http.flask import FlaskApplication


class HTTPServer:
    """HTTP server for handling both WSGI and ASGI applications.
    
    This class determines the appropriate server implementation based on
    the framework (WSGI or ASGI) and debug mode. In debug mode, it always
    uses Flask's development server for simpler debugging.
    
    For production use (debug=False), it tries to use:
    - For WSGI: Gunicorn with sync workers
    - For ASGI: Gunicorn with Uvicorn workers
    
    If dependencies are missing, it falls back to more basic implementations.
    """
    def __init__(self, app, debug, framework="wsgi", **options):
        """Initialize the HTTP server.
        
        Args:
            app: The application to serve (Flask app for WSGI, Starlette app for ASGI)
            debug: Whether to run in debug mode, which always uses Flask's server
            framework: Which framework to use ('wsgi' or 'asgi')
            **options: Additional options to pass to the server
        """
        self.app = app
        self.debug = debug
        self.framework = framework
        self.options = options

        # In debug mode, always use Flask for easier debugging
        if self.debug:
            self.server_class = FlaskApplication
        else:
            # Production server selection
            if self.framework == "asgi":
                try:
                    # For ASGI, try to use Gunicorn with Uvicorn workers
                    from functions_framework._http.asgi import GunicornUvicornApplication
                    self.server_class = GunicornUvicornApplication
                except ImportError:
                    import logging
                    logging.warning(
                        "Failed to import uvicorn worker. Falling back to WSGI server. "
                        "Install uvicorn to use ASGI: pip install uvicorn"
                    )
                    try:
                        # Fall back to regular Gunicorn
                        from functions_framework._http.gunicorn import GunicornApplication
                        self.server_class = GunicornApplication
                    except ImportError:
                        # Ultimate fallback to Flask
                        self.server_class = FlaskApplication
            else:  # default to wsgi
                try:
                    # For WSGI, try to use Gunicorn
                    from functions_framework._http.gunicorn import GunicornApplication
                    self.server_class = GunicornApplication
                except ImportError:
                    # Fall back to Flask
                    self.server_class = FlaskApplication

    def run(self, host, port):
        http_server = self.server_class(
            self.app, host, port, self.debug, **self.options
        )
        http_server.run()


def create_server(app, debug, framework="wsgi", **options):
    """Create an HTTP server for the provided application.
    
    Args:
        app: The application to serve (Flask app for WSGI, Starlette app for ASGI)
        debug: Whether to run in debug mode
        framework: The framework to use ('wsgi' or 'asgi')
        **options: Additional options to pass to the server
        
    Returns:
        An HTTPServer instance
    """
    return HTTPServer(app, debug, framework, **options)
