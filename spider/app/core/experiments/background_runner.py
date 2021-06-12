import asyncio
import aiohttp
from concurrent.futures import ProcessPoolExecutor
from numba import jit
import numpy as np

""" Running a cpu bound task and an io bound task concurrently
"""


def cpu_bound():
    # CPU-bound operations will block the event loop:
    # in general it is preferable to run them in a
    # process pool.
    print("doing computation")
    n = np.zeros((1000,1000), dtype=complex)
    n[60:80, 20:40] = np.exp(1j*np.random.uniform(0, 2*np.pi, (20, 20)))
    im = np.fft.ifftn(n).real
    return im


async def http_requests(urls):
    print("doing io")
    async def fetch(request_client, url):
        async with request_client.get(url) as response:
            result = await response.text()

        return result

    async with aiohttp.ClientSession() as request_client:
        concurrent_fetch_tasks = [asyncio.create_task(fetch(request_client, url)) for url in urls]
        results = await asyncio.gather(*concurrent_fetch_tasks)

    print(len(results))

    return results



async def main(cpu_bound_task, async_task, **kwargs):
    loop = asyncio.get_running_loop()

    async def compute():
        with ProcessPoolExecutor(max_workers=4) as pool:
            result = await loop.run_in_executor(pool, cpu_bound_task)
            print(f"Result: {result}")

    await asyncio.gather(
        asyncio.create_task(compute()),
        asyncio.create_task(async_task(kwargs['urls']))
    )

    # io_results = await async_task(kwargs["urls"])
    # print(len(io_results))


urls=[
    f"https://www.baidu.com/s?wd=asyncio&pn={i}&rsv_spt=1&rsv_iqid=0x8532419c002843d7&issp=1&f=8&rsv_bp=1&rsv_idx=2&ie=utf-8&tn=baiduhome_pg&rsv_dl=tb&rsv_enter=1&rsv_sug3=8&rsv_sug1=7&rsv_sug7=100&rsv_sug2=0&rsv_btype=i&inputT=1935&rsv_sug4=2662"
    for i in range(0, 1000, 10)
]

# asyncio.run(http_requests(urls))

asyncio.run(
    main(cpu_bound, http_requests, urls=urls)
)
