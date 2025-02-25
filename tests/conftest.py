"""Test fixtures for Functions Framework tests."""

import os
import pytest
from starlette.testclient import TestClient
from functions_framework import create_app, create_asgi_app

@pytest.fixture
def temp_function(tmp_path):
    """Create a temporary function file."""
    def _create_function(code):
        func_file = tmp_path / "main.py"
        func_file.write_text(code)
        return str(func_file)
    return _create_function

@pytest.fixture
def test_client():
    """Create a test client for the WSGI application."""
    def _create_client(source, target="function", signature_type="http"):
        app = create_app(target=target, source=source, signature_type=signature_type)
        return TestClient(app)
    return _create_client

@pytest.fixture
def asgi_test_client():
    """Create a test client for the ASGI application."""
    def _create_client(source, target="function", signature_type="http"):
        app = create_asgi_app(target=target, source=source, signature_type=signature_type)
        return TestClient(app)
    return _create_client
