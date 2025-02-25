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

import asyncio
import functions_framework
import httpx
from cloudevents.http.event import CloudEvent
from typing import Dict, Any


@functions_framework.http
async def hello_async_http(request):
    """Example async HTTP function that returns after a short delay."""
    # With Starlette, request is a Starlette Request object
    # With Flask, this function would still work but would run synchronously
    await asyncio.sleep(0.5)  # Simulate an async operation
    return {"message": "Hello async world!"}


@functions_framework.http
async def async_http_with_api(request):
    """Example async HTTP function that makes an API call.
    
    This demonstrates how to make async HTTP requests using httpx.
    """
    # Get parameters from the request
    query_params = dict(request.query_params) if hasattr(request, "query_params") else {}
    user_id = query_params.get("user_id", "1")
    
    # Use httpx for async HTTP calls - this won't block the event loop
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://jsonplaceholder.typicode.com/users/{user_id}")
        user_data = response.json()
    
    # Return a response based on the API data
    return {
        "message": f"Hello, {user_data['name']}!",
        "user_data": user_data
    }


@functions_framework.cloud_event
async def hello_async_cloud_event(cloud_event: CloudEvent):
    """Example async CloudEvent function that processes events."""
    # Process the CloudEvent asynchronously
    await asyncio.sleep(0.5)  # Simulate an async operation
    print(f"Received CloudEvent with ID: {cloud_event['id']} and data {cloud_event.data}")


@functions_framework.http
def hello_sync_http(request) -> Dict[str, Any]:
    """Example synchronous HTTP function."""
    # This works with both Flask and Starlette
    # With Starlette, it runs in a thread pool
    return {"message": "Hello from synchronous function!"}