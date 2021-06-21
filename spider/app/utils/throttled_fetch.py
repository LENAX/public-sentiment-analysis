import asyncio

async def throttled(self, max_concurrency: int, *tasks):
    """ Execute tasks with max concurrency limit
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    loop = asyncio.get_event_loop()

    async def sem_task(task):
        async with semaphore:
            return await task
    return await loop.run_until_complete(
        *(sem_task(task) for task in tasks), return_exceptions=True)
