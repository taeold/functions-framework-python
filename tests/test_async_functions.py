"""Test async function handling in Functions Framework."""

import asyncio
import json
import pytest
import httpx
from starlette.testclient import TestClient
from functions_framework import create_app, create_asgi_app


def test_async_http_function_with_wsgi(temp_function, test_client):
    """Test async HTTP function using WSGI app (Flask)."""
    source = temp_function("""
import asyncio
from flask import jsonify

async def function(request):
    await asyncio.sleep(0.1)
    return jsonify({"message": "Hello Async"})
""")
    
    client = test_client(source)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello Async"}


def test_async_http_function_with_asgi(temp_function):
    """Test async HTTP function using ASGI app (Starlette)."""
    source = temp_function("""
import asyncio

async def function(request):
    await asyncio.sleep(0.1)
    return {"message": "Hello Async ASGI"}
""")
    
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello Async ASGI"}


def test_sync_http_function_with_asgi(temp_function):
    """Test sync HTTP function using ASGI app."""
    source = temp_function("""
def function(request):
    return {"message": "Hello Sync via ASGI"}
""")
    
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello Sync via ASGI"}


def test_async_with_starlette_specific_features(temp_function):
    """Test async function using Starlette-specific features."""
    source = temp_function("""
import asyncio
from starlette.responses import StreamingResponse

async def function(request):
    async def number_generator():
        for i in range(5):
            await asyncio.sleep(0.01)
            yield f"{i}\\n".encode()
            
    return StreamingResponse(number_generator())
""")
    
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.text == "0\n1\n2\n3\n4\n"


def test_async_cloud_event_function(temp_function):
    """Test async CloudEvent function using ASGI app."""
    source = temp_function("""
import asyncio
from cloudevents.http import CloudEvent

async def function(cloud_event):
    await asyncio.sleep(0.1)
    # Just validate that we can access CloudEvent data
    assert cloud_event["id"] is not None
    assert cloud_event.data is not None
    return
""")
    
    app = create_asgi_app(target="function", source=source, signature_type="cloudevent")
    client = TestClient(app)
    
    cloud_event = {
        "specversion": "1.0",
        "type": "example.test",
        "source": "https://example.com/events",
        "id": "123",
        "data": {"message": "Hello"}
    }
    
    response = client.post(
        "/",
        json=cloud_event,
        headers={"Content-Type": "application/cloudevents+json"}
    )
    assert response.status_code == 200


def test_async_background_function_with_asgi(temp_function):
    """Test async background event function using ASGI app."""
    source = temp_function("""
import asyncio

async def function(data, context):
    await asyncio.sleep(0.1)
    assert data["message"] == "Hello"
    assert context.event_id is not None
    return
""")
    
    app = create_asgi_app(target="function", source=source, signature_type="event")
    client = TestClient(app)
    
    event_data = {
        "context": {
            "eventId": "abc123",
            "timestamp": "2020-01-01T00:00:00Z",
            "eventType": "example.event",
            "resource": "example-resource",
        },
        "data": {
            "message": "Hello"
        }
    }
    
    response = client.post("/", json=event_data)
    assert response.status_code == 200


def test_async_function_error_handling(temp_function):
    """Test error handling in async functions with ASGI app."""
    source = temp_function("""
import asyncio

async def function(request):
    await asyncio.sleep(0.1)
    raise ValueError("Test error")
""")
    
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 500
    assert "Test error" in response.text


def test_async_function_with_custom_response(temp_function):
    """Test async function returning custom response with ASGI app."""
    source = temp_function("""
import asyncio
from starlette.responses import JSONResponse

async def function(request):
    await asyncio.sleep(0.1)
    return JSONResponse(
        content={"message": "Custom response"},
        status_code=201,
        headers={"X-Test": "test"}
    )
""")
    
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 201
    assert response.json() == {"message": "Custom response"}
    assert response.headers["X-Test"] == "test"


def test_auto_detection_async(temp_function):
    """Test automatic detection of async function."""
    source = temp_function("""
import asyncio
import functions_framework

@functions_framework.http
async def function(request):
    await asyncio.sleep(0.1)
    return {"detected": "async"}
""")
    
    # The http decorator should register the function as async
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"detected": "async"}


def test_auto_detection_sync(temp_function):
    """Test automatic detection of sync function."""
    source = temp_function("""
import functions_framework

@functions_framework.http
def function(request):
    return {"detected": "sync"}
""")
    
    # The http decorator should register the function as sync
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"detected": "sync"}


def test_execution_context_in_async(temp_function, monkeypatch):
    """Test that execution context is accessible in async functions."""
    source = temp_function("""
import asyncio
import functions_framework
from functions_framework import execution_id

@functions_framework.http
async def function(request):
    # We can access execution context in async functions
    context = execution_id._get_current_context()
    await asyncio.sleep(0.1)
    # Still available after await
    assert context == execution_id._get_current_context()
    return {"execution_id": context.execution_id if context else None}
""")
    
    # Set environment variable to enable execution ID logging
    monkeypatch.setenv("LOG_EXECUTION_ID", "true")
    
    # Set a fixed execution ID for testing
    monkeypatch.setattr(execution_id, "_generate_execution_id", lambda: "test-exec-id")
    
    app = create_asgi_app(target="function", source=source)
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"execution_id": "test-exec-id"}
