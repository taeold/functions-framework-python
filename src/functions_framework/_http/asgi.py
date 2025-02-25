# Copyright 2025 Google LLC
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
import gunicorn.app.base

class GunicornUvicornApplication(gunicorn.app.base.BaseApplication):
    """Gunicorn application that uses Uvicorn workers to serve ASGI applications.
    
    This allows running ASGI applications (like Starlette) using Gunicorn as a process
    manager with Uvicorn workers that properly handle async code.
    """
    def __init__(self, app, host, port, debug, **options):
        """Initialize the Gunicorn application with Uvicorn workers.
        
        Args:
            app: The ASGI application to serve (e.g., Starlette app)
            host: The host to bind to
            port: The port to bind to
            debug: Whether to run in debug mode
            **options: Additional options to pass to Gunicorn
        """
        # Determine sensible worker count - default to CPU count
        cpu_count = os.cpu_count() or 1
        default_workers = 1 if debug else min(cpu_count + 1, 4)
        
        # Default options with good performance settings for async workloads
        self.options = {
            "bind": "%s:%s" % (host, port),
            "workers": int(os.environ.get("WORKERS", default_workers)),
            "worker_class": "uvicorn.workers.UvicornWorker",
            "loglevel": "debug" if debug else os.environ.get("GUNICORN_LOG_LEVEL", "error"),
            "timeout": int(os.environ.get("CLOUD_RUN_TIMEOUT_SECONDS", 0)),
            "limit_request_line": 0,
            # Uvicorn worker specific settings
            "worker_args": ["--loop=auto", "--http=auto"],
        }
        
        # Allow overriding of defaults with passed options
        self.options.update(options)
        self.app = app
        super().__init__()

    def load_config(self):
        """Load configuration from self.options into Gunicorn config."""
        for key, value in self.options.items():
            self.cfg.set(key, value)

    def load(self):
        """Return the application to be run."""
        return self.app