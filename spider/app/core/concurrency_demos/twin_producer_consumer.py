""" Two functions use queue to communicate with each other.
"""
import random
import asyncio
from asyncio import Queue


async def str_to_int(str_queue, int_queue, max_iteration: int):
    # for i in range(max_iteration):
    while True:
        # print(f"\nstr_to_int iteration: {i}")
        print(f"attempting to get string from queue...")
        print(f"queue size: {str_queue.qsize()}")
        s = await str_queue.get()
        print(f"get string {s}, type: {type(s)} from queue.\n")
        print(f"queue size: {str_queue.qsize()}")
        int_value = int(s)
        await asyncio.sleep(random.randint(0, 1))
        str_queue.task_done()
        await int_queue.put(int_value)


async def int_to_str(str_queue, int_queue, max_iteration: int):
    # for i in range(max_iteration):
    while True:
        # print(f"\nint_to_str iteration: {i}")
        print(f"attempting to get integer from queue...")
        print(f"queue size: {int_queue.qsize()}")
        
        number = await int_queue.get()
        print(f"get number {number}, type: {type(number)} from queue.\n")
        print(f"queue size: {int_queue.qsize()}")

        str_value = str(number)
        await asyncio.sleep(random.randint(0, 1))
        int_queue.task_done()
        await str_queue.put(str_value)


async def run_demo(async_task1, async_task2, max_iteration: int):
    int_queue, str_queue = asyncio.Queue(), asyncio.Queue()
    str_queue.put_nowait("123")
    str_queue.put_nowait("567")

    await asyncio.wait([async_task1(str_queue, int_queue, max_iteration),
                        async_task1(str_queue, int_queue, max_iteration),
                        async_task2(str_queue, int_queue, max_iteration)])


asyncio.run(run_demo(str_to_int, int_to_str, 2))
