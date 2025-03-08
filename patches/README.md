# Async Support Patches for Functions Framework Python

This directory contains a series of patches that incrementally add async support to the Functions Framework Python. Each patch builds on the previous one to complete the implementation in logical, reviewable chunks.

## Patches Overview

1. **Core ASGI Infrastructure**: Establishes basic ASGI support using Starlette.
2. **Execution Context for Async**: Adds context management for async functions.
3. **HTTP Function Handlers**: Implements HTTP function handlers for ASGI.
4. **CloudEvent and Background Event**: Adds support for event-based functions.
5. **Typed Event Support**: Implements typed event handlers for ASGI.
6. **Template Rendering**: Adds template support and utilities.
7. **Tests**: Adds comprehensive tests for the async implementation.

## How to Apply

Apply the patches in order using the `git apply` command:

```bash
# From the repository root
git apply patches/01-core-asgi-infrastructure.patch
git apply patches/02-execution-context-for-async.patch
git apply patches/03-http-handlers-for-asgi.patch
git apply patches/04-cloud-event-handlers.patch
git apply patches/05-typed-event-support.patch
git apply patches/06-template-rendering.patch
git apply patches/07-tests.patch
```

Or if you want to apply all patches at once:

```bash
git apply patches/*.patch
```

## Testing After Each Patch

It's recommended to test after applying each patch to ensure everything works correctly:

```bash
pytest
```

Note that some tests will only work after applying all patches, particularly the async tests introduced in patch 7.

## Dependencies

You'll need to install Starlette and other async-related dependencies:

```bash
pip install starlette uvicorn httpx pytest-asyncio
```

## How to Use Async Functions

Once the patches are applied, you can use async functions with the framework:

```python
import asyncio
import functions_framework

@functions_framework.http
async def hello_async(request):
    await asyncio.sleep(0.1)  # Simulate async work
    return {"message": "Hello Async!"}
```

To run this function with the ASGI server:

```bash
functions-framework --target=hello_async --debug
```