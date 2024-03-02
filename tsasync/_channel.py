import inspect
import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Awaitable, Deque, Generic, Optional, Union

from ._event import Event
from ._utils import T, in_loop, wrapret


@dataclass
class OperationContext:
    event: Event
    value: Any
    destination: Optional[Event] = None


class Channel(Generic[T]):
    _ts_lock: threading.RLock
    _queue: Deque[OperationContext]
    _waiters: Deque[Event]
    _max_size: int
    _is_closed: bool

    @property
    def closed(self) -> bool:
        with self._ts_lock:
            return self._is_closed

    def __init__(self, buffered: int = 0):
        """
        Create a new channel
        """
        self._ts_lock = threading.RLock()
        self._queue = deque()
        self._waiters = deque()
        self._max_size = buffered
        self._is_closed = False

    def send(self, value: T) -> Union[Awaitable, None]:
        """
        Send any object to the channel.
        This method locks main thread until receive fired.
        :param value: any object
        """
        if value is None:
            raise ValueError("None is not allowed")

        with self._ts_lock:
            if self._is_closed:
                raise IOError("Channel is closed")

            ctx = OperationContext(event=Event(), value=value)

            # No need to wait because enought buffered slots
            if len(self._queue) < self._max_size:
                ctx.event.set()

            # Put item to the queue
            self._queue.append(ctx)

            # Unlock for waiter in needed
            try:
                event = self._waiters.popleft()
                ctx.destination = event
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
            if len(self._queue) > 0 and len(self._waiters) == 0:
                return wrapret(self._next_item())

            if self._is_closed:
                return wrapret(None)

            # Create event and wait for data
            event = Event()
            self._waiters.append(event)

        # Wait for event
        if in_loop():
            return self._areceive(event)

        # Get item from the queue
        event.wait()
        return self._next_item(event)

    def close(self):
        """
        Close the channel.
        All buffered items will be passed.
        """
        with self._ts_lock:
            self._is_closed = True

            # Unlock for waiter in needed
            while len(self._waiters) > 0:
                try:
                    event = self._waiters.popleft()
                    event.set()
                except IndexError:
                    pass

            # Unlock all senders
            for item in self._queue:
                item.event.set()

    async def _areceive(self, event: Event) -> T:
        """
        Receive item asynchronly
        :param event: event instance
        """
        waiter = event.wait()
        if inspect.isawaitable(waiter):
            await waiter
        return self._next_item(event)

    def _next_item(self, event: Optional[Event] = None) -> T:
        """
        Get next item from the queue
        """
        with self._ts_lock:
            if self._is_closed and len(self._queue) == 0:
                return None
            ctx = self._queue.popleft()
            if ctx.destination is not None:
                assert ctx.destination == event, f"{ctx.destination} != {event}"
            ctx.event.set()
            return ctx.value
