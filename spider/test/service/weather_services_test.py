""" Weather service test cases
"""
import pytest
import asyncio
from uuid import UUID
from datetime import datetime
from ...app.models.data_models import WeatherData
from ...app.models.db_models import Weather
from ...app.models.request_models import QueryArgs
from ...app.service import WeatherService
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
def weather_db_model(database):
    Weather.db = database
    return Weather


@pytest.fixture
def weather_service(weather_db_model):
    return WeatherService(weather_db_model=weather_db_model)


@pytest.fixture
def sample_weather_record_id():
    return "33a055fe-c6d2-53d5-8374-22e2c6886e98"


@pytest.fixture
def sample_weather_record():
    return WeatherData(
        weather_id=UUID("33a055fe-c6d2-53d5-8374-22e2c6886e98"),
        title="武汉历史天气预报2021年6月份",
        province="湖北",
        city="武汉",
        date="2021-6-2",
        weather='多云/多云',
        temperature="32℃/22℃",
        wind="东风1-2级/东风1-2级",
        create_dt="2021-06-29 16:18:04.205417"
    )
    
@pytest.fixture
def sample_query():
    return {"city": "武汉"}


@pytest.mark.asyncio
async def test_get_one_record(weather_service,
                              sample_weather_record_id,
                              sample_weather_record):
    record = await weather_service.get_one(sample_weather_record_id)
    assert record == sample_weather_record


@pytest.mark.asyncio
async def test_get_many_records(weather_service, sample_query):
    records = await weather_service.get_many(sample_query)
    debug(records)
    assert len(records) > 0
    
    for record in records:
        for key in sample_query:
            debug(key)
            debug(record)
            debug(getattr(record, key), sample_query[key])
            
            assert hasattr(record, key)
            assert sample_query[key] == getattr(record, key)


