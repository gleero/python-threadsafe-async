# Asyncio ↔ Thread Synchronisation library

This library provides synchronisation primitives between **asyncio** and **threads** in Python. It allows you to coordinate the execution of **asyncio coroutines** and **threads** using familiar synchronisation primitives such as `Event` and `Channel`.

## Installation

You can install this library using pip:

```
pip install threadsafe-async
```

## Usage

### Event

To use the `Event` class, import it from the library and create an instance:

```
from tsasync import Event

event = Event()
```

You can then use the `wait()`, `set()`, `clear()`, and `is_set()` methods of the `Event` instance to coordinate the execution of asyncio coroutines and threads. For example:

```
async def coroutine(event):
    await event.wait()
    # event is set

def thread(event):
    event.set()
```

You can use the `wait()` method synchronously from the thread

```
event.wait()
```

and asynchronously from the coroutine in event loop:

```
await event.wait()
```


The `wait()` method blocks until the event is set, while the `set()` method sets the event and wakes up all tasks waiting for it. The `clear()` method clears the event, causing tasks waiting for it to block again. The `is_set()` method returns `True` if the event is set, and `False` otherwise.

**Note** that you should only call the `wait()` method from the same thread or asyncio event loop that created the `Event` instance. If you try to call `wait()` from a different thread or event loop, a `RuntimeError` will be raised.

### Channel

It allows you to send and receive data between asyncio coroutines and threads.

To use the `Channel` class, import it from the library and create an instance:

```
from tsasync import Channel

channel = Channel()
```

You can then use the `send()` and `receive()` methods of the `Channel` instance to communicate between asyncio coroutines and threads:

```
async def consumer_coroutine(channel):
   data = await channel.receive()
   ...

def consumer_thread(channel):
   data = channel.receive()
   ...

async def producer_coroutine(channel):
   ...
   await channel.send(data)

def producer_thread(channel):
   ...
   channel.send(data)
```

The `send()` method sends data to the channel, while the `receive()` method receives data from the channel. The `send()` method will block until the receive side of the channel is ready to receive data. The `receive()` method will block until there is data available to be received.

Note that the `send()` and `receive()` methods are will block the main thread if there are using without `await`.

If you want to use a buffered channel with a maximum size, you can pass the buffered argument to the `Channel` constructor:

```
channel = Channel(buffered=10)
```

This will create a channel with a buffer of 10 items. If the buffer is full, the `send()` method will block until there is room in the buffer.


## License

This library is licensed under the MIT License. See the `LICENSE` file for more information.

## Contributing

Contributions are welcome! Please open an issue or pull request on the GitHub repository if you have any suggestions or bug reports.
