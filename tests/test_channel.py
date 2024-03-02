import asyncio
from typing import Optional

import pytest
from utils import PropagatingThread, all_for_one

from tsasync import Channel


async def asender(ch: Channel[Optional[int]], data: list, close: bool = False):
    for item in data:
        await ch.send(item)
    if close:
        ch.close()


async def areceiver(ch: Channel[int]) -> list:
    ret = []
    while True:
        item = await ch.receive()
        if item is None:
            break
        ret.append(item)
    return ret


def ssender(ch: Channel[Optional[int]], data: list, close: bool = False):
    for item in data:
        ch.send(item)
    if close:
        ch.close()


def sreceiver(ch: Channel[int]) -> list:
    ret = []
    while True:
        item = ch.receive()
        if item is None:
            break
        ret.append(item)
    return ret


@pytest.mark.asyncio
async def test_channel_between_async_and_coroutine_sender():
    channel = Channel[Optional[int]]()
    sender_task = asyncio.create_task(asender(channel, [1, 2, 3, 4, 5], close=True))
    result = []
    while True:
        item = await channel.receive()
        if item is None:
            break
        result.append(item)
    await sender_task
    assert result == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_channel_between_async_and_many_coroutine_senders():
    channel = Channel[Optional[int]]()
    senders = []
    for x in range(5):
        senders.append(asyncio.create_task(asender(channel, [1, 2])))
    result = []
    for x in range(10):
        item = await channel.receive()
        result.append(item)
    await asyncio.gather(*senders)
    channel.close()
    assert await channel.receive() is None
    assert len(result) == 10


@pytest.mark.asyncio
async def test_channel_between_async_and_many_mixed_senders():
    channel = Channel[Optional[int]]()
    senders_coro = []
    senders_threads = []
    for x in range(5):
        senders_coro.append(asyncio.create_task(asender(channel, [1, 2])))
        t = PropagatingThread(target=ssender, args=(channel, [3, 4]))
        t.start()
        senders_threads.append(t)

    result = []
    for x in range(20):
        item = await channel.receive()
        result.append(item)
    await asyncio.gather(*senders_coro)
    for t in senders_threads:
        t.join()
    channel.close()
    assert await channel.receive() is None
    assert len(result) == 20


@pytest.mark.asyncio
async def test_channel_between_async_and_coroutine_receiver():
    channel = Channel[Optional[int]]()
    receiver_task = asyncio.create_task(areceiver(channel))
    for item in [1, 2, 3, 4, 5]:
        await channel.send(item)
    channel.close()
    result = await receiver_task
    assert result == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_channel_between_async_and_many_coroutine_receivers():
    channel = Channel[Optional[int]]()
    receivers = []
    for x in range(7):
        receivers.append(asyncio.create_task(areceiver(channel)))
    for item in list(range(50)):
        await channel.send(item)
    channel.close()
    result = list(all_for_one(await asyncio.gather(*receivers)))
    assert sorted(result) == list(range(50))


@pytest.mark.asyncio
async def test_channel_between_async_and_many_mixed_receivers():
    channel = Channel[Optional[int]]()
    receivers_coro = []
    receivers_threads = []
    for x in range(7):
        receivers_coro.append(asyncio.create_task(areceiver(channel)))
        t = PropagatingThread(target=sreceiver, args=(channel,))
        t.start()
        receivers_threads.append(t)
    for item in list(range(100)):
        await channel.send(item)
    channel.close()
    result = list(all_for_one(await asyncio.gather(*receivers_coro)))
    for t in receivers_threads:
        t.join()
        result += t.ret
    assert sorted(result) == list(range(100))


@pytest.mark.asyncio
async def test_channel_between_two_coroutines():
    channel = Channel[Optional[int]]()
    sender_task = asyncio.create_task(asender(channel, [1, 2, 3, 4, 5], close=True))
    receiver_task = asyncio.create_task(areceiver(channel))
    await sender_task
    result = await receiver_task
    assert result == [1, 2, 3, 4, 5]


def test_channel_between_two_threads():
    channel = Channel[Optional[int]]()
    sender_thread = PropagatingThread(
        target=ssender, args=(channel, [1, 2, 3, 4, 5], True)
    )
    sender_thread.start()
    receiver_thread = PropagatingThread(target=sreceiver, args=(channel,))
    receiver_thread.start()
    sender_thread.join()
    receiver_thread.join()
    assert receiver_thread.ret == [1, 2, 3, 4, 5]


def test_channel_between_sync_and_thread_sender():
    channel = Channel[Optional[int]]()
    result = []
    sender_thread = PropagatingThread(
        target=ssender, args=(channel, [1, 2, 3, 4, 5], True)
    )
    sender_thread.start()
    while True:
        item = channel.receive()
        if item is None:
            break
        result.append(item)
    sender_thread.join()
    assert result == [1, 2, 3, 4, 5]


def test_channel_between_sync_and_thread_receiver():
    channel = Channel[Optional[int]]()
    receiver_thread = PropagatingThread(target=sreceiver, args=(channel,))
    receiver_thread.start()
    for item in [1, 2, 3, 4, 5]:
        channel.send(item)
    channel.close()
    receiver_thread.join()
    assert receiver_thread.ret == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_channel_between_async_and_thread_sender():
    channel = Channel[Optional[int]]()
    result = []
    sender_thread = PropagatingThread(
        target=ssender, args=(channel, [1, 2, 3, 4, 5], True)
    )
    sender_thread.start()
    while True:
        item = await channel.receive()
        if item is None:
            break
        result.append(item)
    sender_thread.join()
    assert result == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_channel_between_async_and_thread_receiver():
    channel = Channel[Optional[int]]()
    receiver_thread = PropagatingThread(target=sreceiver, args=(channel,))
    receiver_thread.start()
    for item in [1, 2, 3, 4, 5]:
        await channel.send(item)
    channel.close()
    receiver_thread.join()
    assert receiver_thread.ret == [1, 2, 3, 4, 5]


def test_channel_not_closed():
    channel = Channel[Optional[int]]()
    assert channel.closed is False


def test_channel_closed():
    channel = Channel[Optional[int]]()
    channel.close()
    assert channel.closed is True


def test_channel_send_if_closed():
    channel = Channel[Optional[int]]()
    channel.close()
    with pytest.raises(IOError):
        channel.send(1)


def test_channel_send_none():
    channel = Channel[Optional[int]]()
    with pytest.raises(ValueError):
        channel.send(None)


@pytest.mark.asyncio
async def test_channel_close_buffered_read():
    channel = Channel[Optional[int]](buffered=100)
    for x in range(10):
        await channel.send(x)
    channel.close()
    for x in range(10):
        assert await channel.receive() == x
    assert await channel.receive() is None


@pytest.mark.asyncio
async def test_channel_close_many_mixed_pending_receive():
    channel = Channel[Optional[int]]()
    receivers_coros = []
    receivers_threads = []
    for x in range(10):
        receivers_coros.append(asyncio.create_task(areceiver(channel)))
        receiver_thread = PropagatingThread(target=sreceiver, args=(channel,))
        receiver_thread.start()
    channel.close()
    await asyncio.gather(*receivers_coros)
    for t in receivers_threads:
        t.join()


@pytest.mark.asyncio
async def test_channel_close_waiting_async_sender():
    channel = Channel[Optional[int]]()
    sender_task = asyncio.create_task(asender(channel, [1, 2], close=False))
    assert (await channel.receive()) == 1
    await asyncio.sleep(0.5)
    channel.close()
    await sender_task
