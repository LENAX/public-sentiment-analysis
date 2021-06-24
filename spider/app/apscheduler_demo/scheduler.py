import asyncio
from pytz import utc
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import (
    ThreadPoolExecutor, ProcessPoolExecutor
)
from apscheduler.executors.asyncio import AsyncIOExecutor
from pymongo import MongoClient
from ..db import create_client


db_client = create_client(host='localhost',
                          username='admin',
                          password='root',
                          port=27017,
                          db_name='spiderDB')
client = MongoClient('mongodb://admin:root@localhost:27017/spiderDB?authSource=admin')
jobstores = {
    'mongo': MongoDBJobStore(client=client)
}
executors = {
    'default': AsyncIOExecutor(),
    'processpool': ProcessPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc
)

async def test_job():
    print("started!")
    print("working...!")
    await asyncio.sleep(5)
    print("finished!")


async def tick():
    print('Tick! The time is: %s' % datetime.now())

if __name__ == "__main__":
    # loop = asyncio.new_event_loop()
    scheduler.start()
    job = scheduler.add_job(
        test_job, name=None, trigger='interval', seconds=5)
    print(job.next_run_time)
    print(scheduler.get_jobs())
    
    
    try:  
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    # async_task = tick()
    # print(type(async_task))
