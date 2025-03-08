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

"""Function used to test template rendering with Starlette in async context."""
import asyncio


async def function(request):
    """Test HTTP function that renders a template using Starlette.
    
    Args:
        request: The Starlette Request object
        
    Returns:
        A TemplateResponse with the rendered template
    """
    # Access templates from app state
    templates = request.app.state.templates
    
    # Get message from query parameters or default to "World"
    message = request.query_params.get("message", "World")
    
    # Simulate some async processing
    await asyncio.sleep(0.1)
    
    # Render template with context
    return templates.TemplateResponse("hello.html", {"request": request, "name": message})