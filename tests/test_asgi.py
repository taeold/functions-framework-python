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
import platform
import sys
import pytest
import pretend

from functions_framework._http.asgi import GunicornUvicornApplication


@pytest.mark.skipif("platform.system() == 'Windows'")
@pytest.mark.parametrize("debug", [True, False])
def test_gunicorn_uvicorn_application(debug):
    app = pretend.stub()
    host = "1.2.3.4"
    port = "1234"
    options = {}

    gunicorn_app = GunicornUvicornApplication(app, host, port, debug, **options)

    assert gunicorn_app.app == app
    assert gunicorn_app.options == {
        "bind": "%s:%s" % (host, port),
        "workers": 1,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "loglevel": "debug" if debug else "error",
        "timeout": 0,
        "limit_request_line": 0,
    }

    assert gunicorn_app.cfg.bind == ["1.2.3.4:1234"]
    assert gunicorn_app.cfg.workers == 1
    assert gunicorn_app.cfg.worker_class == "uvicorn.workers.UvicornWorker"
    assert gunicorn_app.cfg.timeout == 0
    assert gunicorn_app.load() == app


@pytest.mark.skipif("platform.system() == 'Windows'")
def test_gunicorn_uvicorn_application_options():
    """Test that custom options are respected."""
    app = pretend.stub()
    host = "1.2.3.4"
    port = "1234"
    options = {
        "workers": 4,
        "loglevel": "warning",
        "timeout": 120,
    }

    gunicorn_app = GunicornUvicornApplication(app, host, port, False, **options)

    assert gunicorn_app.options["workers"] == 4
    assert gunicorn_app.options["loglevel"] == "warning"
    assert gunicorn_app.options["timeout"] == 120
    assert gunicorn_app.options["worker_class"] == "uvicorn.workers.UvicornWorker"

    assert gunicorn_app.cfg.workers == 4
    assert gunicorn_app.cfg.timeout == 120