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

"""Function used to test handling async functions using typed decorators."""
import asyncio
from typing import Any, Type, TypeVar, cast

import functions_framework

T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


class AsyncTestType:
    name: str
    age: int

    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    @staticmethod
    def from_dict(obj: dict) -> "AsyncTestType":
        name = from_str(obj.get("name"))
        age = from_int(obj.get("age"))
        return AsyncTestType(name, age)

    def to_dict(self) -> dict:
        result: dict = {}
        result["name"] = from_str(self.name)
        result["age"] = from_int(self.age)
        return result


@functions_framework.typed(AsyncTestType)
async def async_function_typed(testType: AsyncTestType):
    """Async function that returns a typed object.
    
    Args:
        testType: The input typed object
        
    Returns:
        The same object with the age incremented by 1
    """
    # Simulate some async processing
    await asyncio.sleep(0.1)
    # Modify the object
    testType.age += 1
    return testType


@functions_framework.typed(AsyncTestType)
async def async_function_typed_string_return(testType: AsyncTestType):
    """Async function that returns a string.
    
    Args:
        testType: The input typed object
        
    Returns:
        A string greeting
    """
    # Simulate some async processing
    await asyncio.sleep(0.1)
    return f"Hello {testType.name}, you are {testType.age} years old"