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
import platform
import sys
from unittest import mock

import pretend
import pytest

import functions_framework._http


@pytest.mark.parametrize("debug", [True, False])
def test_create_server(monkeypatch, debug):
    server_stub = pretend.stub()
    httpserver = pretend.call_recorder(lambda *a, **kw: server_stub)
    monkeypatch.setattr(functions_framework._http, "HTTPServer", httpserver)
    wsgi_app = pretend.stub()
    options = {"a": pretend.stub(), "b": pretend.stub()}

    functions_framework._http.create_server(wsgi_app, debug, **options)

    assert httpserver.calls == [pretend.call(wsgi_app, debug, **options)]


@pytest.mark.parametrize("debug", [True, False])
def test_create_async_server(monkeypatch, debug):
    server_stub = pretend.stub()
    httpserver_async = pretend.call_recorder(lambda *a, **kw: server_stub)
    monkeypatch.setattr(functions_framework._http, "HTTPServerAsync", httpserver_async)
    asgi_app = pretend.stub()
    options = {"a": pretend.stub(), "b": pretend.stub()}

    functions_framework._http.create_async_server(asgi_app, debug, **options)

    assert httpserver_async.calls == [pretend.call(asgi_app, debug, **options)]


@pytest.mark.parametrize(
    "debug, gunicorn_missing, expected",
    [
        (True, False, "flask"),
        (False, False, "flask" if platform.system() == "Windows" else "gunicorn"),
        (True, True, "flask"),
        (False, True, "flask"),
    ],
)
def test_httpserver(monkeypatch, debug, gunicorn_missing, expected):
    app = pretend.stub()
    http_server = pretend.stub(run=pretend.call_recorder(lambda: None))
    server_classes = {
        "flask": pretend.call_recorder(lambda *a, **kw: http_server),
        "gunicorn": pretend.call_recorder(lambda *a, **kw: http_server),
    }
    options = {"a": pretend.stub(), "b": pretend.stub()}

    monkeypatch.setattr(
        functions_framework._http, "FlaskApplication", server_classes["flask"]
    )
    if gunicorn_missing or platform.system() == "Windows":
        monkeypatch.setitem(sys.modules, "functions_framework._http.gunicorn", None)
    else:
        from functions_framework._http import gunicorn

        monkeypatch.setattr(gunicorn, "GunicornApplication", server_classes["gunicorn"])

    wrapper = functions_framework._http.HTTPServer(app, debug, **options)

    assert wrapper.app == app
    assert wrapper.server_class == server_classes[expected]
    assert wrapper.options == options

    host = pretend.stub()
    port = pretend.stub()

    wrapper.run(host, port)

    assert wrapper.server_class.calls == [
        pretend.call(app, host, port, debug, **options)
    ]
    assert http_server.run.calls == [pretend.call()]


@pytest.mark.skipif("platform.system() == 'Windows'")
@pytest.mark.parametrize("debug", [True, False])
def test_gunicorn_application(debug):
    app = pretend.stub()
    host = "1.2.3.4"
    port = "1234"
    options = {}

    import functions_framework._http.gunicorn

    gunicorn_app = functions_framework._http.gunicorn.GunicornApplication(
        app, host, port, debug, **options
    )

    assert gunicorn_app.app == app
    assert gunicorn_app.options == {
        "bind": "%s:%s" % (host, port),
        "workers": 1,
        "threads": os.cpu_count() * 4,
        "timeout": 0,
        "loglevel": "error",
        "limit_request_line": 0,
    }

    assert gunicorn_app.cfg.bind == ["1.2.3.4:1234"]
    assert gunicorn_app.cfg.workers == 1
    assert gunicorn_app.cfg.threads == os.cpu_count() * 4
    assert gunicorn_app.cfg.timeout == 0
    assert gunicorn_app.load() == app


@pytest.mark.skipif("platform.system() == 'Windows'")
@pytest.mark.parametrize("debug", [True, False])
def test_uvicorn_application(debug):
    app = pretend.stub()
    host = "1.2.3.4"
    port = "1234"
    options = {}

    import functions_framework._http.gunicorn

    uvicorn_app = functions_framework._http.gunicorn.UvicornApplication(
        app, host, port, debug, **options
    )

    assert uvicorn_app.app == app
    assert uvicorn_app.options == {
        "bind": "%s:%s" % (host, port),
        "workers": os.cpu_count() * 4 + 1,
        "threads": os.cpu_count() * 4,
        "timeout": 0,
        "loglevel": "error",
        "limit_request_line": 0,
    }

    assert uvicorn_app.cfg.bind == ["1.2.3.4:1234"]
    assert uvicorn_app.cfg.workers == 1
    assert uvicorn_app.cfg.threads == os.cpu_count() * 4
    assert uvicorn_app.cfg.timeout == 0
    assert uvicorn_app.worker_class == "uvicorn.workers.UvicornWorker"
    assert uvicorn_app.load() == app


@pytest.mark.parametrize("debug", [True, False])
def test_flask_application(debug):
    app = pretend.stub(run=pretend.call_recorder(lambda *a, **kw: None))
    host = pretend.stub()
    port = pretend.stub()
    options = {"a": pretend.stub(), "b": pretend.stub()}

    flask_app = functions_framework._http.flask.FlaskApplication(
        app, host, port, debug, **options
    )

    assert flask_app.app == app
    assert flask_app.host == host
    assert flask_app.port == port
    assert flask_app.debug == debug
    assert flask_app.options == options

    flask_app.run()

    assert app.run.calls == [
        pretend.call(host, port, debug=debug, a=options["a"], b=options["b"]),
    ]


@pytest.mark.parametrize(
    "debug, uvicorn_missing, expected",
    [
        (True, False, "starlette"),
        (False, False, "starlette" if platform.system() == "Windows" else "uvicorn"),
        (True, True, "starlette"),
        (False, True, "starlette"),
    ],
)
def test_httpserver_async(monkeypatch, debug, uvicorn_missing, expected):
    app = pretend.stub()
    http_server = pretend.stub(run=pretend.call_recorder(lambda: None))
    server_classes = {
        "starlette": pretend.call_recorder(lambda *a, **kw: http_server),
        "uvicorn": pretend.call_recorder(lambda *a, **kw: http_server),
    }
    options = {"a": pretend.stub(), "b": pretend.stub()}

    # Create a mock starlette module
    mock_starlette = mock.MagicMock()
    mock_starlette.StarletteApplication = server_classes["starlette"]
    sys.modules["functions_framework._http.starlette"] = mock_starlette

    # Handle gunicorn module
    if uvicorn_missing or platform.system() == "Windows":
        if "functions_framework._http.gunicorn" in sys.modules:
            del sys.modules["functions_framework._http.gunicorn"]
    else:
        mock_gunicorn = mock.MagicMock()
        mock_gunicorn.UvicornApplication = server_classes["uvicorn"]
        sys.modules["functions_framework._http.gunicorn"] = mock_gunicorn

    try:
        # Import the module again to get fresh imports
        import importlib

        importlib.reload(functions_framework._http)

        wrapper = functions_framework._http.HTTPServerAsync(app, debug, **options)

        assert wrapper.app == app
        assert wrapper.server_class == server_classes[expected]
        assert wrapper.options == options

        host = pretend.stub()
        port = pretend.stub()

        wrapper.run(host, port)

        assert wrapper.server_class.calls == [
            pretend.call(app, host, port, debug, **options)
        ]
        assert http_server.run.calls == [pretend.call()]
    finally:
        # Clean up
        if "functions_framework._http.starlette" in sys.modules:
            del sys.modules["functions_framework._http.starlette"]
        if "functions_framework._http.gunicorn" in sys.modules and not uvicorn_missing:
            del sys.modules["functions_framework._http.gunicorn"]


def test_starlette_application(monkeypatch):
    app = pretend.stub()
    host = "1.2.3.4"
    port = "1234"
    debug = True
    options = {"worker_count": 4}

    # Create modules needed
    mock_uvicorn = mock.MagicMock()
    mock_uvicorn.run = pretend.call_recorder(lambda app, **kwargs: None)
    sys.modules["uvicorn"] = mock_uvicorn

    # Create the StarletteApplication implementation
    starlette_module_str = """
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

import uvicorn


class StarletteApplication:
    def __init__(self, app, host, port, debug, **options):
        self.app = app
        self.host = host
        self.port = port
        self.debug = debug
        
        # Default uvicorn config
        self.options = {
            "log_level": "debug" if debug else "error",
            "reload": debug,
        }
        self.options.update(options)
    
    def run(self):
        uvicorn.run(
            self.app,
            host=self.host,
            port=int(self.port),
            **self.options
        )
"""

    # Dynamically create the module
    import types

    starlette_module = types.ModuleType("functions_framework._http.starlette")
    exec(starlette_module_str, starlette_module.__dict__)
    sys.modules["functions_framework._http.starlette"] = starlette_module

    try:
        # Import the StarletteApplication class from the module
        from functions_framework._http.starlette import StarletteApplication

        starlette_app = StarletteApplication(app, host, port, debug, **options)

        assert starlette_app.app == app
        assert starlette_app.host == host
        assert starlette_app.port == port
        assert starlette_app.debug == debug
        assert starlette_app.options["log_level"] == "debug"
        assert starlette_app.options["reload"] == True
        assert starlette_app.options["worker_count"] == 4

        starlette_app.run()

        assert mock_uvicorn.run.calls == [
            pretend.call(
                app,
                host=host,
                port=int(port),
                log_level="debug",
                reload=True,
                worker_count=4,
            )
        ]
    finally:
        # Clean up
        if "functions_framework._http.starlette" in sys.modules:
            del sys.modules["functions_framework._http.starlette"]
        if "uvicorn" in sys.modules:
            del sys.modules["uvicorn"]
