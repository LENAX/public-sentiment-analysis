import asyncio
from typing import List, TypeVar

Coroutine = TypeVar("Coroutine")

async def throttled(max_concurrency: int, tasks: List[Coroutine]):
    """ Execute tasks with max concurrency limit
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    loop = asyncio.get_event_loop()

    async def sem_task(task):
        async with semaphore:
            return await task
    return await asyncio.gather(*(sem_task(task) for task in tasks), 
                                return_exceptions=True)
