""" News service test cases
"""
import pytest
import asyncio
from uuid import UUID
from datetime import datetime
from ...app.models.data_models import NewsData
from ...app.models.db_models import News
from ...app.models.request_models import QueryArgs
from ...app.service import NewsService
from ...app.db.client import create_client
from devtools import debug


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def database():
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name="spiderDB")
    return db_client['spiderDB']


@pytest.fixture
def news_db_model(database):
    News.db = database
    return News


@pytest.fixture
def news_service(news_db_model):
    return NewsService(news_db_model=news_db_model)


@pytest.fixture
def sample_news_record_id():
    return "fcf55955-7f70-56bc-bdab-1d29a717ee2f"


@pytest.fixture
def sample_news_record():
    return NewsData(
        news_id=UUID("fcf55955-7f70-56bc-bdab-1d29a717ee2f"),
        url="https://baijiahao.baidu.com/s?id=1700923518035740113&wfr=spider&for=pc",
        title="广州、深圳疫情全梳理:感染者之间有何关系?",
        author="广州及深圳市卫健委",
        publish_time="2021-05-27 22:49:00",
        content="21日广州市荔湾区出现新冠肺炎确诊病例后,截至5月27日14时,广州市累计报告确诊病例4例、无症状感染者5例,均与确诊病例郭某有关联。21日,深圳盐田港西作业区在例行检查中发现一例无症状感染者。截至目前累计诊断9例无症状感染者,其中6例参加过5月17日的一次国际货轮作业。",
        images=[]
    )


@pytest.fixture
def sample_query():
    return {"author": "广州及深圳市卫健委"}


@pytest.mark.asyncio
async def test_get_one_record(news_service,
                              sample_news_record_id,
                              sample_news_record):
    record = await news_service.get_one(sample_news_record_id)
    assert record == sample_news_record


@pytest.mark.asyncio
async def test_get_many_records(news_service, sample_query):
    records = await news_service.get_many(sample_query)
    debug(records)
    assert len(records) > 0

    for record in records:
        for key in sample_query:
            debug(key)
            debug(record)
            debug(getattr(record, key), sample_query[key])

            assert hasattr(record, key)
            assert sample_query[key] == getattr(record, key)
