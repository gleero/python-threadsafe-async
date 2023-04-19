import asyncio
from typing import Awaitable, TypeVar, Union


T = TypeVar("T")


def in_loop() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def wrapret(value: T) -> Union[T, Awaitable[T]]:
    if in_loop():
        result: asyncio.Future = asyncio.Future()
        result.set_result(value)
        return result
    return value
