import asyncio
from typing import Optional

import pytest
from utils import PropagatingThread, all_for_one

from tsasync import Channel


async def asender(ch: Channel[Optional[int]], data: list):
    for item in data:
        await ch.send(item)
    await ch.send(None)


async def areceiver(ch: Channel[int]) -> list:
    ret = []
    while True:
        item = await ch.receive()
        if item is None:
            break
        ret.append(item)
    return ret


def ssender(ch: Channel[Optional[int]], data: list):
    for item in data:
        ch.send(item)
    ch.send(None)


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
    sender_task = asyncio.create_task(asender(channel, [1, 2, 3, 4, 5]))
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
    cnt = 0
    while True:
        item = await channel.receive()
        if item is None:
            cnt += 1
        else:
            result.append(item)
        if cnt == 5:
            break
    await asyncio.gather(*senders)
    assert len(result) == 10


@pytest.mark.asyncio
async def test_channel_between_async_and_many_mixed_senders():
    channel = Channel[Optional[int]]()
    senders_coro = []
    senders_threads = []
    for x in range(5):
        senders_coro.append(
            asyncio.create_task(asender(channel, [1, 2]))
        )
        t = PropagatingThread(target=ssender, args=(channel, [3, 4]))
        t.start()
        senders_threads.append(t)

    result = []
    cnt = 0
    while True:
        item = await channel.receive()
        if item is None:
            cnt += 1
        else:
            result.append(item)
        if cnt == 10:
            break
    await asyncio.gather(*senders_coro)
    for t in senders_threads:
        t.join()
    assert len(result) == 20


@pytest.mark.asyncio
async def test_channel_between_async_and_coroutine_receiver():
    channel = Channel[Optional[int]]()
    receiver_task = asyncio.create_task(areceiver(channel))
    for item in [1, 2, 3, 4, 5]:
        await channel.send(item)
    await channel.send(None)
    result = await receiver_task
    assert result == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_channel_between_async_and_many_coroutine_receivers():
    channel = Channel[Optional[int]]()
    receivers = []
    rcv_count = 7
    for x in range(rcv_count):
        receivers.append(asyncio.create_task(areceiver(channel)))
    for item in list(range(50)):
        await channel.send(item)
    for x in range(rcv_count):
        await channel.send(None)
    result = list(all_for_one(await asyncio.gather(*receivers)))
    assert sorted(result) == list(range(50))


@pytest.mark.asyncio
async def test_channel_between_async_and_many_mixed_receivers():
    channel = Channel[Optional[int]]()
    receivers_coro = []
    receivers_threads = []
    rcv_count = 7
    for x in range(rcv_count):
        receivers_coro.append(asyncio.create_task(areceiver(channel)))
        t = PropagatingThread(target=sreceiver, args=(channel,))
        t.start()
        receivers_threads.append(t)
    for item in list(range(100)):
        await channel.send(item)
    for x in range(rcv_count * 2):
        await channel.send(None)
    result = list(all_for_one(await asyncio.gather(*receivers_coro)))
    for t in receivers_threads:
        t.join()
        result += t.ret
    assert sorted(result) == list(range(100))


@pytest.mark.asyncio
async def test_channel_between_two_coroutines():
    channel = Channel[Optional[int]]()
    sender_task = asyncio.create_task(asender(channel, [1, 2, 3, 4, 5]))
    receiver_task = asyncio.create_task(areceiver(channel))
    await sender_task
    result = await receiver_task
    assert result == [1, 2, 3, 4, 5]


def test_channel_between_two_threads():
    channel = Channel[Optional[int]]()
    sender_thread = PropagatingThread(
        target=ssender, args=(channel, [1, 2, 3, 4, 5])
    )
    sender_thread.start()
    receiver_thread = PropagatingThread(
        target=sreceiver, args=(channel,)
    )
    receiver_thread.start()
    sender_thread.join()
    receiver_thread.join()
    assert receiver_thread.ret == [1, 2, 3, 4, 5]


def test_channel_between_sync_and_thread_sender():
    channel = Channel[Optional[int]]()
    result = []
    sender_thread = PropagatingThread(
        target=ssender, args=(channel, [1, 2, 3, 4, 5])
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
    receiver_thread = PropagatingThread(
        target=sreceiver, args=(channel,)
    )
    receiver_thread.start()
    for item in [1, 2, 3, 4, 5]:
        channel.send(item)
    channel.send(None)
    receiver_thread.join()
    assert receiver_thread.ret == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_channel_between_async_and_thread_sender():
    channel = Channel[Optional[int]]()
    result = []
    sender_thread = PropagatingThread(
        target=ssender, args=(channel, [1, 2, 3, 4, 5])
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
    receiver_thread = PropagatingThread(
        target=sreceiver, args=(channel,)
    )
    receiver_thread.start()
    for item in [1, 2, 3, 4, 5]:
        await channel.send(item)
    await channel.send(None)
    receiver_thread.join()
    assert receiver_thread.ret == [1, 2, 3, 4, 5]
