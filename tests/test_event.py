import asyncio
import threading

import pytest
from utils import PropagatingThread

from tsasync import Event


def test_event_create_noloop():
    event = Event()
    assert event.loop is None


@pytest.mark.asyncio
async def test_event_create_loop():
    event = Event()
    assert event.loop is not None


def test_event_is_set_noloop():
    event = Event()
    assert event.loop is None
    assert event.is_set() is False


@pytest.mark.asyncio
async def test_event_is_set_loop():
    event = Event()
    assert event.is_set() is False


def test_event_set_noloop():
    event = Event()
    event.set()
    assert event.loop is None
    assert event.is_set() is True


@pytest.mark.asyncio
async def test_event_set_loop():
    event = Event()
    event.set()
    assert event.is_set() is True


def test_event_clear_noloop():
    event = Event()
    event.set()
    event.clear()
    assert event.loop is None
    assert event.is_set() is False


@pytest.mark.asyncio
async def test_event_clear_loop():
    event = Event()
    event.set()
    event.clear()
    assert event.is_set() is False


def test_event_wait_immediately_noloop():
    event = Event()
    event.set()
    assert event.loop is None
    assert event.wait() is True
    assert event.loop is None


def test_event_wait_immediately_postloop():
    async def async_wait(e: Event):
        assert await e.wait() is True

    event = Event()
    event.set()
    assert event.loop is None
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_wait(event))
    assert event.loop is not None


@pytest.mark.asyncio
async def test_event_wait_immediately_loop():
    event = Event()
    event.set()
    assert await event.wait() is True


@pytest.mark.asyncio
async def test_event_wait_same_loop():
    event = Event()

    async def setter():
        event.set()

    task = asyncio.create_task(setter())
    assert await event.wait() is True
    assert event.is_set() is True
    await task


@pytest.mark.asyncio
async def test_event_wait_from_other_thread():
    def set_event_thread(e: Event):
        e.set()

    event = Event()
    thread = threading.Thread(target=set_event_thread, args=(event,))
    thread.start()
    assert await event.wait() is True
    assert event.is_set() is True
    thread.join()


def test_event_wait_in_other_thread_noloop():
    def wait_event_thread(e: Event, me: threading.Event):
        assert e.is_set() is False
        me.set()
        me.wait()
        assert e.wait() is True
        assert e.is_set() is True

    mgm_event = threading.Event()
    event = Event()
    thread = PropagatingThread(target=wait_event_thread, args=(event, mgm_event))
    thread.start()
    mgm_event.wait()
    mgm_event.clear()
    mgm_event.set()
    event.set()
    thread.join()


def test_event_wait_in_other_thread_postloop():
    def wait_event_thread(e: Event, me: threading.Event):
        async def async_wait(ev: Event):
            assert await ev.wait() is True

        assert e.is_set() is False
        me.set()
        me.wait()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(async_wait(e))
        assert e.is_set() is True
        loop.close()

    mgm_event = threading.Event()
    event = Event()
    thread = PropagatingThread(target=wait_event_thread, args=(event, mgm_event))
    thread.start()
    mgm_event.wait()
    mgm_event.clear()
    mgm_event.set()
    event.set()
    thread.join()


@pytest.mark.asyncio
async def test_event_wait_in_other_thread_loop():
    def wait_event_thread(e: Event, me: threading.Event):
        async def async_wait(ev: Event):
            assert await ev.wait() is True

        loop = asyncio.new_event_loop()
        assert e.is_set() is False
        me.set()
        me.wait()
        loop.run_until_complete(async_wait(e))
        assert e.is_set() is True
        loop.close()

    mgm_event = threading.Event()
    event = Event()
    thread = PropagatingThread(target=wait_event_thread, args=(event, mgm_event))
    thread.start()
    mgm_event.wait()
    mgm_event.clear()
    mgm_event.set()
    event.set()
    thread.join()
    assert event.loop != asyncio.get_event_loop()
    with pytest.raises(RuntimeError):
        await event.wait()
