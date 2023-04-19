import asyncio
import threading
from asyncio import Event as _AsyncEvent
from threading import Event as _SyncEvent, RLock
from typing import Awaitable, Optional, Union

from ._utils import in_loop, wrapret


class Event:
    _loop: Optional[asyncio.AbstractEventLoop]
    _async_ev: Optional[_AsyncEvent]
    _sync_ev: _SyncEvent
    _ts_lock: RLock
    _wait_thread_id: int
    _tmp_state: bool

    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        with self._ts_lock:
            return self._loop

    def __init__(self):
        self._wait_thread_id = -1
        self._ts_lock = RLock()
        self._loop = None
        self._async_ev = None
        self._sync_ev = _SyncEvent()
        self._tmp_state = False
        self._reinit()

    def _reinit(self):
        """
        Reinit home event loop and event instance
        """
        with self._ts_lock:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
            else:
                self._async_ev = _AsyncEvent()
                if self._tmp_state:
                    self._async_ev.set()

    def set(self):
        """
        Set the event.

        All tasks waiting for event to be set will be
        immediately awakened.
        """
        with self._ts_lock:
            self._tmp_state = True
            self._sync_ev.set()
            if self._async_ev is None:
                return

            if (
                threading.get_ident() == self._wait_thread_id
                or self._wait_thread_id == -1
            ):
                self._async_ev.set()
            else:
                self._loop.call_soon_threadsafe(self._async_ev.set)

    def clear(self):
        """
        Clear (unset) the event.

        Tasks awaiting on `wait()` will now block until
        the `set()` method is called again.
        """
        with self._ts_lock:
            self._tmp_state = False
            if self._async_ev is not None:
                self._async_ev.clear()
            if self._sync_ev is not None:
                self._sync_ev.clear()

    def is_set(self):
        """
        Return `True` if the event is set.
        """
        with self._ts_lock:
            return self._tmp_state

    def wait(self) -> Union[Awaitable[bool], bool]:
        """
        Wait until the event is set.

        If the event is set, return True immediately.
        Otherwise, block until another task calls `set()`.
        """
        inloop = in_loop()

        with self._ts_lock:
            # Current thread now is default for this Event
            if self._wait_thread_id == -1:
                self._wait_thread_id = threading.get_ident()

                # Event loop changed, update states
                if inloop:
                    if self._loop != asyncio.get_running_loop():
                        self._loop = None
                        self._async_ev = None
                        self._reinit()

            # Prevent for waits in different threads
            if self._wait_thread_id != threading.get_ident():
                raise RuntimeError("Using wait in different threads are not allowed")

            # Reinit loop if not exists
            if inloop and self._loop is None:
                self._reinit()

        # Return immediately is set
        if self.is_set():
            return wrapret(True)

        # Wait for event
        if inloop:
            if self._async_ev is None:
                raise RuntimeError("Event loop not found")
            return self._async_ev.wait()

        else:
            return self._sync_ev.wait()
