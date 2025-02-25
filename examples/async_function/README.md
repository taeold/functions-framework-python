# Async Functions Example

This example demonstrates how to use asynchronous functions with the Functions Framework using the ASGI framework (Starlette).

## Requirements

```
pip install functions-framework[asgi]
```

This installs the additional dependencies needed for ASGI support (Starlette, Uvicorn, and httpx).

## Running the example

### Basic async HTTP function

Run the async HTTP function that simply returns a response after a delay:

```bash
functions-framework --target=hello_async_http --framework=asgi
```

In another terminal, test the HTTP function:

```bash
curl localhost:8080
```

### Async HTTP function with API calls

Run the async HTTP function that makes external API calls:

```bash
functions-framework --target=async_http_with_api --framework=asgi
```

In another terminal, test the function with a parameter:

```bash
curl "localhost:8080?user_id=2"
```

### Async CloudEvent function

Run the CloudEvent function:

```bash
functions-framework --target=hello_async_cloud_event --signature-type=cloudevent --framework=asgi
```

In another terminal, test the CloudEvent function:

```bash
curl -X POST localhost:8080 \
  -H "Content-Type: application/cloudevents+json" \
  -d '{
    "specversion" : "1.0",
    "type" : "example.com.cloud.event",
    "source" : "https://example.com/cloudevents/pull",
    "subject" : "123",
    "id" : "A234-1234-1234",
    "time" : "2018-04-05T17:31:00Z",
    "data" : "hello world"
}'
```

### Sync function running in ASGI mode

The Functions Framework can also run synchronous functions in ASGI mode:

```bash
functions-framework --target=hello_sync_http --framework=asgi
```

## How it works

The Functions Framework now supports two execution models:

1. WSGI (Default) - Using Flask and Gunicorn
2. ASGI - Using Starlette and Uvicorn workers

When you use `--framework=asgi`, the Functions Framework creates a Starlette application and runs it with Gunicorn using Uvicorn workers. This allows you to write asynchronous functions using `async/await` syntax.

The framework automatically detects if your function is synchronous or asynchronous and handles it appropriately:
- Async functions are executed directly in the async context
- Sync functions are executed in a thread pool to avoid blocking the event loop

### Benefits of async functions

Asynchronous functions can provide significant performance benefits for I/O-bound operations like:

1. Database queries
2. HTTP requests to external APIs
3. File operations
4. Handling multiple concurrent requests

The example `async_http_with_api` demonstrates how to make asynchronous HTTP requests using httpx, which is a modern HTTP client that supports async/await. This allows your function to make external API calls without blocking the event loop, enabling it to handle other requests while waiting for the API response.

Both synchronous and asynchronous functions can be executed in either framework, but asynchronous functions only gain their performance benefits when run with the ASGI framework.