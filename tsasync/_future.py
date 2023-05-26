import asyncio
import sys
import threading
from asyncio import Future as AsyncFuture
from threading import RLock
from typing import Any, Generator, Generic, Optional

from ._utils import T


class Future(AsyncFuture, Generic[T]):
    _ts_lock: RLock
    _ev_loop: asyncio.AbstractEventLoop
    _main_thread_id: int

    def __init__(self, *args, **kwargs):
        try:
            self._ev_loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError("There is no current event loop")
        super().__init__(*args, **kwargs)
        self._main_thread_id = threading.get_ident()
        self._ts_lock = RLock()

    def __await__(self) -> Generator[Any, None, T]:
        with self._ts_lock:
            return super().__await__()

    def result(self) -> T:
        with self._ts_lock:
            return super().result()

    def done(self) -> bool:
        with self._ts_lock:
            return super().done()

    def cancelled(self) -> bool:
        with self._ts_lock:
            return super().cancelled()

    def cancel(self, msg: Optional[Any] = None) -> bool:
        with self._ts_lock:
            if sys.version_info >= (3, 9):
                return super().cancel(msg)
            else:
                return super().cancel()

    def exception(self) -> Optional[BaseException]:
        with self._ts_lock:
            return super().exception()

    def set_result(self, result: T) -> None:
        with self._ts_lock:
            if self._main_thread_id == threading.get_ident():
                super().set_result(result)
            else:
                self._ev_loop.call_soon_threadsafe(super().set_result, result)

    def set_exception(self, exception: BaseException) -> None:
        with self._ts_lock:
            if self._main_thread_id == threading.get_ident():
                super().set_exception(exception)
            else:
                self._ev_loop.call_soon_threadsafe(super().set_exception, exception)
