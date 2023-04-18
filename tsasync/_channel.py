import inspect
import threading
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Deque, Generic, Union

from ._event import Event
from ._utils import T, in_loop, wrapret


class ChannelState(Enum):
    IDLE = 1


@dataclass
class OperationContext:
    event: Event
    value: Any


class Channel(Generic[T]):
    _ts_lock: threading.RLock
    _queue: Deque[OperationContext]
    _waiters: Deque[Event]
    _max_size: int

    def __init__(self, buffered: int = 0):
        """
        Create a new channel
        """
        self._ts_lock = threading.RLock()
        self._queue = deque()
        self._waiters = deque()
        self._max_size = buffered

    def send(self, value: T) -> Union[Awaitable, None]:
        """
        Send any object to the channel.
        This method locks main thread until receive fired.
        :param value: any object
        """
        ctx = OperationContext(event=Event(), value=value)

        with self._ts_lock:
            # No need to wait because enought buffered slots
            if len(self._queue) < self._max_size:
                ctx.event.set()

            # Put item to the queue
            self._queue.append(ctx)

            # Unlock for waiter in needed
            try:
                event = self._waiters.popleft()
                event.set()
            except IndexError:
                pass

        # Return awaitable object if in loop
        if in_loop():
            waiter = ctx.event.wait()
            if inspect.isawaitable(waiter):
                return waiter
            return None

        # Blocking wait if not in loop
        ctx.event.wait()
        return None

    def receive(self) -> Union[T, Awaitable[T]]:
        """
        Get item from the queue
        """
        with self._ts_lock:
            # Queue has pending objects, return it immediately
            if len(self._queue) > 0:
                return wrapret(self._next_item())

            # Create event and wait for data
            event = Event()
            self._waiters.append(event)

        # Wait for event
        if in_loop():
            return self._areceive(event)

        # Get item from the queue
        event.wait()
        with self._ts_lock:
            return self._next_item()

    async def _areceive(self, event: Event) -> T:
        """
        Receive item asynchronly
        :param event: event instance
        """
        waiter = event.wait()
        if inspect.isawaitable(waiter):
            await waiter
        with self._ts_lock:
            return self._next_item()

    def _next_item(self) -> T:
        """
        Get next item from the queue
        """
        ctx = self._queue.popleft()
        ctx.event.set()
        return ctx.value
