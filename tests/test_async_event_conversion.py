# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import json
import pytest
import pretend
from cloudevents.http.event import CloudEvent
from functions_framework import event_conversion
from functions_framework.exceptions import EventConversionException


@pytest.mark.asyncio
async def test_marshal_background_event_data_async():
    """Test marshalling Pub/Sub data asynchronously."""
    # Create a request mock with appropriate data
    message_id = "123"
    publish_time = "2020-03-11T22:38:41.118Z"
    message_data = "Test data"
    
    # Create a mock async request object with get_json coroutine
    async def mock_get_json():
        return {
            "subscription": "projects/project-id/subscriptions/subscription-id",
            "message": {
                "messageId": message_id,
                "publishTime": publish_time,
                "data": message_data,
                "attributes": {
                    "attr1": "value1"
                }
            }
        }
    
    request = pretend.stub(
        get_json=mock_get_json,
        path="/projects/project-id/topics/topic-id"
    )
    
    # Call the async marshaller
    result = await event_conversion.marshal_background_event_data_async(request)
    
    # Verify the result
    assert result["context"]["eventId"] == message_id
    assert result["context"]["timestamp"] == publish_time
    assert result["context"]["eventType"] == event_conversion._PUBSUB_EVENT_TYPE
    assert result["context"]["resource"]["service"] == event_conversion._PUBSUB_CE_SERVICE
    assert result["context"]["resource"]["type"] == event_conversion._PUBSUB_MESSAGE_TYPE
    assert result["context"]["resource"]["name"] == "projects/project-id/topics/topic-id"
    assert result["data"]["@type"] == event_conversion._PUBSUB_MESSAGE_TYPE
    assert result["data"]["data"] == message_data
    assert result["data"]["attributes"]["attr1"] == "value1"


@pytest.mark.asyncio
async def test_background_event_to_cloud_event_async():
    """Test converting background event to CloudEvent asynchronously."""
    # Create a request mock with appropriate data
    event_id = "123"
    timestamp = "2020-03-11T22:38:41.118Z"
    event_type = "google.pubsub.topic.publish"
    resource = {
        "service": "pubsub.googleapis.com",
        "name": "projects/project-id/topics/topic-id",
        "type": "type.googleapis.com/google.pubsub.v1.PubsubMessage"
    }
    data = {
        "@type": "type.googleapis.com/google.pubsub.v1.PubsubMessage",
        "data": "Test data",
        "attributes": {"attr1": "value1"}
    }
    
    # Create a mock async request object with get_json coroutine
    async def mock_get_json():
        return {
            "context": {
                "eventId": event_id,
                "timestamp": timestamp,
                "eventType": event_type,
                "resource": resource
            },
            "data": data
        }
    
    request = pretend.stub(get_json=mock_get_json)
    
    # Call the async converter
    cloud_event = await event_conversion.background_event_to_cloud_event_async(request)
    
    # Verify the CloudEvent
    assert isinstance(cloud_event, CloudEvent)
    assert cloud_event["id"] == event_id
    assert cloud_event["time"] == timestamp
    assert cloud_event["type"] == "google.cloud.pubsub.topic.v1.messagePublished"
    assert cloud_event["source"] == "//pubsub.googleapis.com/projects/project-id/topics/topic-id"
    assert "message" in cloud_event.data


@pytest.mark.asyncio
async def test_cloud_event_to_background_event_async():
    """Test converting CloudEvent to background event asynchronously."""
    # Create CloudEvent data
    cloud_event_data = {
        "specversion": "1.0",
        "id": "123",
        "source": "//pubsub.googleapis.com/projects/project-id/topics/topic-id",
        "type": "google.cloud.pubsub.topic.v1.messagePublished",
        "time": "2020-03-11T22:38:41.118Z",
        "data": {
            "message": {
                "data": "VGVzdCBkYXRh",  # Base64 encoded "Test data"
                "attributes": {
                    "attr1": "value1"
                }
            }
        }
    }
    
    # Create headers
    headers = {
        "ce-specversion": "1.0",
        "ce-id": "123",
        "ce-source": "//pubsub.googleapis.com/projects/project-id/topics/topic-id",
        "ce-type": "google.cloud.pubsub.topic.v1.messagePublished",
        "ce-time": "2020-03-11T22:38:41.118Z",
        "content-type": "application/json"
    }
    
    # Create mock async request
    async def mock_body():
        return json.dumps(cloud_event_data).encode()
    
    request = pretend.stub(
        body=mock_body,
        headers=headers
    )
    
    # Call the async converter
    data, context = await event_conversion.cloud_event_to_background_event_async(request)
    
    # Verify the result
    assert context.event_id == "123"
    assert context.timestamp == "2020-03-11T22:38:41.118Z"
    assert context.event_type == "google.pubsub.topic.publish"
    assert context.resource["service"] == "pubsub.googleapis.com"
    assert context.resource["name"] == "projects/project-id/topics/topic-id"
    assert "message" in data


@pytest.mark.asyncio
async def test_marshal_background_event_data_async_invalid():
    """Test marshalling invalid data asynchronously."""
    # Create a mock async request object with get_json that returns invalid data
    async def mock_get_json():
        return {}
    
    request = pretend.stub(
        get_json=mock_get_json,
        path="/projects/project-id/topics/topic-id"
    )
    
    # Call the async marshaller - should return the data as is since it's not a Pub/Sub payload
    result = await event_conversion.marshal_background_event_data_async(request)
    assert result == {}