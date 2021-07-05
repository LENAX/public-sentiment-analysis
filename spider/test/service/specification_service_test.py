""" Specification service test cases
"""
import pytest
import asyncio
from uuid import UUID
from datetime import datetime
from ...app.models.data_models import SpecificationData
from ...app.models.db_models import Specification
from ...app.models.request_models import (
    QueryArgs, ScrapeRules, KeywordRules, TimeRange, ParsingPipeline)
from ...app.enums import JobType, Parser
from ...app.service import SpecificationService
from ...app.db.client import create_client
from devtools import debug
from os import getcwd
from yaml import Loader, load, dump, Dumper
from typing import Any, Callable

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
                              db_name="test")
    return db_client['test']


def load_service_config(
        config_name: str,
        loader_func: Callable = load,
        loader_class: Any = Loader,
        config_class: Any = ScrapeRules,
        config_path: str = f"{getcwd()}/spider/app/service_configs"
    ) -> object:
    with open(f"{config_path}/{config_name}.yml", "r") as f:
        config_text = f.read()
        parsed_obj = loader_func(config_text, Loader=loader_class)
        config_obj = config_class.parse_obj(parsed_obj)
        return config_obj


spec_store = {}

@pytest.fixture
def weather_scrape_rule():
    return load_service_config("weather_config")

@pytest.fixture
def aqi_scrape_rule():
    return load_service_config("aqi_config")

@pytest.fixture
def news_scrape_rule():
    return load_service_config("baidu_news")


@pytest.fixture
def covid_scrape_rule():
    return load_service_config("covid_report")


@pytest.fixture
def weather_specification(weather_scrape_rule):
    return SpecificationData(
        urls=["http://www.tianqihoubao.com/lishi"],
        job_type=JobType.WEATHER_REPORT,
        scrape_rules=weather_scrape_rule
    )

@pytest.fixture
def aqi_specification(aqi_scrape_rule):
    return SpecificationData(
        urls=["http://www.tianqihoubao.com/aqi"],
        job_type=JobType.AIR_QUALITY_REPORT,
        scrape_rules=aqi_scrape_rule
    )

@pytest.fixture
def news_specification(news_scrape_rule):
    return SpecificationData(
        urls=["http://www.baidu.com/s?tn=news&ie=utf-8"],
        job_type=JobType.BAIDU_NEWS_SCRAPING,
        scrape_rules=news_scrape_rule
    )

@pytest.fixture
def covid_report_specification(covid_scrape_rule):
    return SpecificationData(
        urls=[
            "https://voice.baidu.com/act/newpneumonia/newpneumonia",
            "https://voice.baidu.com/act/newpneumonia/newpneumonia#tab4"],
        job_type=JobType.COVID_REPORT,
        scrape_rules=covid_scrape_rule
    )
    
    
@pytest.fixture
def updated_news_urls():
    return [
        "http://www.baidu.com/s?tn=news&ie=utf-8",
        "http://www.guancha.cn"
    ]
    

@pytest.fixture
def updated_city_keywords():
    return [
        "foshan",
        "maoming",
        "jiangmen"
    ]


@pytest.fixture
def updated_time_range():
    return TimeRange(
        start_date=datetime(2021,1,1),
        end_date=datetime(2021,5,1)
    )
    

@pytest.fixture
def updated_day_range():
    return TimeRange(past_days=14)


@pytest.fixture
def updated_pipeline():
    return ParsingPipeline(
        name="test_pipeline",
        parser=Parser.GENERAL_NEWS_PARSER,
        parse_rules=[]
    )


@pytest.fixture
def specification_db_model(database):
    Specification.db = database
    return Specification


@pytest.fixture
def specification_service(specification_db_model):
    return SpecificationService(specification_db_model=specification_db_model)



@pytest.mark.asyncio
async def test_add_weather_spec(specification_service, weather_specification):
    spec = await specification_service.add_one(weather_specification)
    if weather_specification.specification_id is None:
        weather_specification.specification_id = spec.specification_id
    assert spec == weather_specification
    debug(spec)
    spec_store['weather'] = spec

@pytest.mark.asyncio
async def test_add_news_spec(specification_service, news_specification):
    spec = await specification_service.add_one(news_specification)
    if news_specification.specification_id is None:
        news_specification.specification_id = spec.specification_id
    assert spec == news_specification
    spec_store['news'] = spec


@pytest.mark.asyncio
async def test_add_aqi_spec(specification_service, aqi_specification):
    spec = await specification_service.add_one(aqi_specification)
    if aqi_specification.specification_id is None:
        aqi_specification.specification_id = spec.specification_id
    assert spec == aqi_specification
    spec_store['aqi'] = spec
    

@pytest.mark.asyncio
async def test_add_covid_spec(specification_service, covid_report_specification):
    spec = await specification_service.add_one(covid_report_specification)
    if covid_report_specification.specification_id is None:
        covid_report_specification.specification_id = spec.specification_id
    assert spec == covid_report_specification
    spec_store['covid'] = spec
    

@pytest.mark.asyncio
async def test_get_weather_spec(specification_service,
                                weather_specification):
    spec_id = spec_store['weather'].specification_id
    weather_specification.specification_id = spec_id
    record = await specification_service.get_one(spec_id)
    assert record == weather_specification
    
@pytest.mark.asyncio
async def test_get_aqi_spec(specification_service,
                            aqi_specification):
    spec_id = spec_store['aqi'].specification_id
    aqi_specification.specification_id = spec_id
    record = await specification_service.get_one(spec_id)
    assert record == aqi_specification
    
@pytest.mark.asyncio
async def test_get_covid_spec(specification_service,
                              covid_report_specification):
    spec_id = spec_store['covid'].specification_id
    covid_report_specification.specification_id = spec_id
    record = await specification_service.get_one(spec_id)
    assert record == covid_report_specification
    

@pytest.mark.asyncio
async def test_get_news_spec(specification_service,
                             news_specification):
    spec_id = spec_store['news'].specification_id
    news_specification.specification_id = spec_id
    record = await specification_service.get_one(spec_id)
    assert record == news_specification


@pytest.mark.asyncio
async def test_update_urls(specification_service, updated_news_urls):
    spec_id = spec_store['news'].specification_id
    record = await specification_service.get_one(spec_id)
    record.urls = updated_news_urls
    await specification_service.update_one(spec_id, record)
    updated_record = await specification_service.get_one(spec_id)
    updated_urls = updated_record.urls
    assert all([updated_url == url
                for updated_url, url in zip(updated_urls, updated_news_urls)])


@pytest.mark.asyncio
async def test_update_keyword(specification_service, updated_city_keywords):
    spec_id = spec_store['aqi'].specification_id
    record = await specification_service.get_one(spec_id)
    record.scrape_rules.keywords.include = updated_city_keywords
    await specification_service.update_one(spec_id, record)
    updated_record = await specification_service.get_one(spec_id)
    updated_keywords = updated_record.scrape_rules.keywords.include
    assert all([updated_kw == kw
                for updated_kw, kw in zip(updated_keywords, updated_city_keywords)])


@pytest.mark.asyncio
async def test_update_day_range(specification_service, updated_day_range):
    spec_id = spec_store['news'].specification_id
    record = await specification_service.get_one(spec_id)
    record.scrape_rules.time_range = updated_day_range
    await specification_service.update_one(spec_id, record)
    updated_record = await specification_service.get_one(spec_id)
    updated_past_days = updated_record.scrape_rules.time_range.past_days
    assert updated_past_days == updated_day_range.past_days

@pytest.mark.asyncio
async def test_update_time_range(specification_service, updated_time_range):
    spec_id = spec_store['weather'].specification_id
    record = await specification_service.get_one(spec_id)
    record.scrape_rules.time_range = updated_time_range
    await specification_service.update_one(spec_id, record)
    updated_record = await specification_service.get_one(spec_id)
    assert updated_record.scrape_rules.time_range.start_date == updated_time_range.start_date
    assert updated_record.scrape_rules.time_range.end_date == updated_time_range.end_date
    

@pytest.mark.asyncio
async def test_update_pipeline(specification_service, updated_pipeline):
    spec_id = spec_store['covid'].specification_id
    record = await specification_service.get_one(spec_id)
    record.scrape_rules.parsing_pipeline = [updated_pipeline]
    await specification_service.update_one(spec_id, record)
    updated_record = await specification_service.get_one(spec_id)
    updated_parsing_pipeline = updated_record.scrape_rules.parsing_pipeline
    assert updated_parsing_pipeline[0] == updated_pipeline



# @pytest.mark.asyncio
# async def test_delete_many_records(specification_service):
#     await specification_service.delete_many({})
#     records = await specification_service.get_many({})
#     assert len(records) == 0
