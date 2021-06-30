""" COVIDReport service test cases
"""
import pytest
import asyncio
from uuid import UUID
from datetime import datetime
from ...app.models.data_models import COVIDReportData
from ...app.models.db_models import COVIDReport
from ...app.models.request_models import QueryArgs
from ...app.service import COVIDReportService
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
def covid_report_db_model(database):
    COVIDReport.db = database
    return COVIDReport


@pytest.fixture
def covid_report_service(covid_report_db_model):
    return COVIDReportService(covid_report_db_model=covid_report_db_model)


@pytest.fixture
def sample_covid_report_record_id():
    return "fbb19233-d29f-593a-8e80-2bec6d9dd0b2"


@pytest.fixture
def sample_covid_report_record():
    return COVIDReportData(
        covid_report_id=UUID("fbb19233-d29f-593a-8e80-2bec6d9dd0b2"),
        report_type="国内疫情",
        last_update="2021-06-26 15:13:00",
        confirmed_cases="4,576",
        new_asymptomatic_cases="472",
        suspicious_cases="0",
        serious_symptom_cases="14",
        imported_cases="6,526",
        total_deaths="5,469",
        total_cured="108,180",
        total_confirmed_cases="118,225",
        create_dt="2021-06-26 15:13:27.737364"
    )


@pytest.fixture
def sample_query():
    return {"report_type": "国内疫情"}


@pytest.mark.asyncio
async def test_get_one_record(covid_report_service,
                              sample_covid_report_record_id,
                              sample_covid_report_record):
    record = await covid_report_service.get_one(sample_covid_report_record_id)
    debug(record)
    assert record == sample_covid_report_record


@pytest.mark.asyncio
async def test_get_many_records(covid_report_service, sample_query):
    records = await covid_report_service.get_many(sample_query)
    debug(records)
    assert len(records) > 0

    for record in records:
        for key in sample_query:
            debug(key)
            debug(record)
            debug(getattr(record, key), sample_query[key])

            assert hasattr(record, key)
            assert sample_query[key] == getattr(record, key)
