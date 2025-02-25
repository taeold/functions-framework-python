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

import pretend
import pytest

import functions_framework._http


@pytest.mark.parametrize("debug, framework", [
    (True, "wsgi"),
    (False, "wsgi"),
    (True, "asgi"),
    (False, "asgi"),
])
def test_create_server(monkeypatch, debug, framework):
    server_stub = pretend.stub()
    httpserver = pretend.call_recorder(lambda *a, **kw: server_stub)
    monkeypatch.setattr(functions_framework._http, "HTTPServer", httpserver)
    app = pretend.stub()
    options = {"a": pretend.stub(), "b": pretend.stub()}

    functions_framework._http.create_server(app, debug, framework, **options)

    assert httpserver.calls == [pretend.call(app, debug, framework, **options)]


@pytest.mark.parametrize(
    "debug, framework, gunicorn_missing, uvicorn_missing, expected",
    [
        # WSGI tests
        (True, "wsgi", False, False, "flask"),
        (False, "wsgi", False, False, "flask" if platform.system() == "Windows" else "gunicorn"),
        (True, "wsgi", True, False, "flask"),
        (False, "wsgi", True, False, "flask"),
        
        # ASGI tests
        (True, "asgi", False, False, "flask"),  # Debug mode always uses Flask even for ASGI
        (False, "asgi", False, False, "gunicorn_uvicorn"),
        (False, "asgi", False, True, "gunicorn"),  # Fallback to regular Gunicorn if Uvicorn missing
        (False, "asgi", True, False, "flask"),  # Fallback to Flask if Gunicorn missing
    ],
)
def test_httpserver(monkeypatch, debug, framework, gunicorn_missing, uvicorn_missing, expected):
    app = pretend.stub()
    http_server = pretend.stub(run=pretend.call_recorder(lambda: None))
    server_classes = {
        "flask": pretend.call_recorder(lambda *a, **kw: http_server),
        "gunicorn": pretend.call_recorder(lambda *a, **kw: http_server),
        "gunicorn_uvicorn": pretend.call_recorder(lambda *a, **kw: http_server),
    }
    options = {"a": pretend.stub(), "b": pretend.stub()}

    # Set up the Flask application class
    monkeypatch.setattr(
        functions_framework._http, "FlaskApplication", server_classes["flask"]
    )
    
    # Handle Gunicorn imports
    if gunicorn_missing or platform.system() == "Windows":
        monkeypatch.setitem(sys.modules, "functions_framework._http.gunicorn", None)
    else:
        from functions_framework._http import gunicorn
        monkeypatch.setattr(gunicorn, "GunicornApplication", server_classes["gunicorn"])
    
    # Handle ASGI imports
    if uvicorn_missing:
        monkeypatch.setitem(sys.modules, "functions_framework._http.asgi", None)
    else:
        # Only mock this if we're not mocking gunicorn as missing
        if not gunicorn_missing:
            try:
                from functions_framework._http import asgi
                monkeypatch.setattr(asgi, "GunicornUvicornApplication", server_classes["gunicorn_uvicorn"])
            except ImportError:
                # If the module doesn't exist yet (during test development), create a mock
                asgi_module = types.ModuleType("functions_framework._http.asgi")
                asgi_module.GunicornUvicornApplication = server_classes["gunicorn_uvicorn"]
                sys.modules["functions_framework._http.asgi"] = asgi_module
                monkeypatch.setattr(functions_framework._http, "asgi", asgi_module)

    wrapper = functions_framework._http.HTTPServer(app, debug, framework, **options)

    assert wrapper.app == app
    assert wrapper.server_class == server_classes[expected]
    assert wrapper.options == options
    assert wrapper.framework == framework

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
