""" AirQuality service test cases
"""
import pytest
import asyncio
from uuid import UUID
from datetime import datetime
from ...app.models.data_models import AirQualityData
from ...app.models.db_models import AirQuality
from ...app.models.request_models import QueryArgs
from ...app.service import AirQualityService
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
def air_quality_db_model(database):
    AirQuality.db = database
    return AirQuality


@pytest.fixture
def air_quality_service(air_quality_db_model):
    return AirQualityService(air_quality_db_model=air_quality_db_model)


@pytest.fixture
def sample_air_quality_record_id():
    return "5bdf4d45-95d1-588b-895d-798397b4317d"


@pytest.fixture
def sample_air_quality_record():
    return AirQualityData(
        air_quality_id=UUID("5bdf4d45-95d1-588b-895d-798397b4317d"),
        title="2021年3月深圳空气质量指数AQI_PM2.5历史数据",
        province="深圳",
        city="深圳",
        date="2021-03-01",
        quality='优',
        AQI="31",
        AQI_rank="125",
        PM10="31",
        SO2="6",
        NO2="34",
        Co="0.62",
        O3="48"
    )


@pytest.fixture
def sample_query():
    return {"city": "深圳"}


@pytest.mark.asyncio
async def test_get_one_record(air_quality_service,
                              sample_air_quality_record_id,
                              sample_air_quality_record):
    record = await air_quality_service.get_one(sample_air_quality_record_id)
    assert record == sample_air_quality_record


@pytest.mark.asyncio
async def test_get_many_records(air_quality_service, sample_query):
    records = await air_quality_service.get_many(sample_query)
    debug(records)
    assert len(records) > 0

    for record in records:
        for key in sample_query:
            debug(key)
            debug(record)
            debug(getattr(record, key), sample_query[key])

            assert hasattr(record, key)
            assert sample_query[key] == getattr(record, key)
