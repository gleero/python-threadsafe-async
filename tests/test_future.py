import asyncio
from asyncio import InvalidStateError

import pytest
from utils import PropagatingThread

from tsasync import Future


async def do_result(f: Future[str]):
    f.set_result("hello world")


async def do_error(exc: Exception, f: Future[str]):
    try:
        raise exc
    except Exception as e:
        f.set_exception(e)


def do_result_thread(f: Future[str]):
    f.set_result("hello world")


def do_error_thread(exc: Exception, f: Future[str]):
    try:
        raise exc
    except Exception as e:
        f.set_exception(e)


def test_without_event_loop():
    with pytest.raises(RuntimeError):
        Future()


@pytest.mark.asyncio
async def test_is_future():
    f = Future[str]()
    assert asyncio.isfuture(f)


@pytest.mark.asyncio
async def test_future_await():
    f = Future[str]()
    task = asyncio.create_task(do_result(f))
    assert await f == "hello world"
    await task


@pytest.mark.asyncio
async def test_future_result():
    f = Future[str]()
    task = asyncio.create_task(do_result(f))
    await task
    assert f.result() == "hello world"


@pytest.mark.asyncio
async def test_future_result_no_data():
    f = Future[str]()
    with pytest.raises(InvalidStateError):
        f.result()


@pytest.mark.asyncio
async def test_future_done():
    f = Future[str]()
    assert not f.done()
    task = asyncio.create_task(do_result(f))
    assert not f.done()
    await task
    assert f.done()


@pytest.mark.asyncio
async def test_error_await():
    f = Future[str]()
    task = asyncio.create_task(do_error(ValueError(), f))
    with pytest.raises(ValueError):
        await f
    await task


@pytest.mark.asyncio
async def test_error_result():
    f = Future[str]()
    task = asyncio.create_task(do_error(ValueError(), f))
    await task
    with pytest.raises(ValueError):
        f.result()


@pytest.mark.asyncio
async def test_future_await_thread():
    f = Future[str]()
    thread = PropagatingThread(target=do_result_thread, args=(f,))
    thread.start()
    assert await f == "hello world"
    thread.join()


@pytest.mark.asyncio
async def test_future_result_thread():
    f = Future[str]()
    thread = PropagatingThread(target=do_result_thread, args=(f,))
    thread.start()
    thread.join()
    await asyncio.sleep(0)  # Tick event loop
    assert f.result() == "hello world"


@pytest.mark.asyncio
async def test_future_error_thread():
    f = Future[str]()
    thread = PropagatingThread(target=do_error_thread, args=(ValueError(), f))
    thread.start()
    with pytest.raises(ValueError):
        assert await f == "hello world"
    thread.join()


@pytest.mark.asyncio
async def test_future_get_exception_thread():
    f = Future[str]()
    thread = PropagatingThread(target=do_error_thread, args=(ValueError(), f))
    thread.start()
    thread.join()
    await asyncio.sleep(0)  # Tick event loop
    assert type(f.exception()) == ValueError
