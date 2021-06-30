""" JobService test using Spider services
"""
import pytest
import asyncio
from ...app.models.data_models import (
    RequestHeader, HTMLData, CrawlResult,
    SpecificationData, JobData
)
from ...app.models.db_models import (
    Result, Weather, AirQuality, COVIDReport, News,
    Specification, Job
)
from ...app.models.request_models import (
    QueryArgs, ScrapeRules, KeywordRules, TimeRange, ParsingPipeline)
from ...app.enums import JobType, Parser
from ...app.service import (
    SpiderFactory, AsyncJobService, HTMLSpiderService,
    BaiduCOVIDSpider, BaiduNewsSpider, WeatherSpiderService
)
from ...app.db.client import create_client
from ...app.core import (
    BaseSpider, ParserContextFactory,
    BaseRequestClient, AsyncBrowserRequestClient, RequestClient,
    CrawlerContextFactory, Spider
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from devtools import debug
from typing import Any, Callable
from pytz import utc


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


@pytest.fixture
def specification_db_model(database):
    Specification.db = database
    return Specification


@pytest.fixture
async def weather_spec(specification_db_model):
    spec = await specification_db_model.get_one(
        {"job_type": "weather_report"})
    return spec


@pytest.fixture
async def aqi_spec(specification_db_model):
    spec = await specification_db_model.get_one(
        {"job_type": "air_quality"})
    return spec


@pytest.fixture
async def news_spec(specification_db_model):
    spec = await specification_db_model.get_one(
        {"job_type": "baidu_news_scraping"})
    return spec


@pytest.fixture
async def covid_spec(specification_db_model):
    spec = await specification_db_model.get_one(
        {"job_type": "baidu_covid_report"})
    return spec

@pytest.fixture
def headers():
    return RequestHeader(
        accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    ).dict()

@pytest.fixture
def cookies():
    cookie_text = """BIDUPSID=C2730507E1C86942858719FD87A61E58;
    PSTM=1591763607; BAIDUID=0145D8794827C0813A767D21ADED26B4:FG=1;
    BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek;
    __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BD_UPN=123253; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5;
    H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP;
    """
    cookie_strings = cookie_text.replace("\n", "").replace(" ", "").split(";")
    kookies = {}
    for cookie_str in cookie_strings:
        try:
            key, value = cookie_str.split("=")
            kookies[key] = value
        except IndexError:
            print(cookie_str)
        except ValueError:
            print(cookie_str)
    return kookies

@pytest.fixture
async def request_client(headers, cookies):
    client = await RequestClient(headers=headers, cookies=cookies)
    yield client
    await client.close()

@pytest.fixture
async def browser_client(headers, cookies):
    client = await AsyncBrowserRequestClient(headers=headers, cookies=[cookies])
    yield client
    await client.close()

@pytest.fixture
def spider_class():
    return Spider

@pytest.fixture
def parse_strategy_factory():
    return ParserContextFactory

@pytest.fixture
def crawling_strategy_factory():
    return CrawlerContextFactory
    
@pytest.fixture
def news_model():
    return News

@pytest.fixture
def covid_model():
    return COVIDReport
   
@pytest.fixture
def weather_model():
    return Weather

@pytest.fixture
def aqi_model():
    return AirQuality

@pytest.fixture
def news_spider_service(request_client,
                        spider_class,
                        parse_strategy_factory,
                        news_model):
    spider_service = BaiduNewsSpider(request_client=request_client,
                                     spider_class=spider_class,
                                     parse_strategy_factory=parse_strategy_factory,
                                     result_db_model=news_model)
    return spider_service


@pytest.fixture
def covid_spider_service(request_client,
                         spider_class,
                         parse_strategy_factory,
                         covid_model):
    spider_service = BaiduCOVIDSpider(request_client=request_client,
                                      spider_class=spider_class,
                                      parse_strategy_factory=parse_strategy_factory,
                                      result_db_model=covid_model)
    return spider_service


@pytest.fixture
def weather_spider_service(request_client,
                           spider_class,
                           parse_strategy_factory,
                           crawling_strategy_factory,
                           weather_model):
    spider_service = WeatherSpiderService(request_client=request_client,
                                          spider_class=spider_class,
                                          parse_strategy_factory=parse_strategy_factory,
                                          crawling_strategy_factory=crawling_strategy_factory,
                                          result_db_model=weather_model)
    return spider_service


@pytest.fixture
def aqi_spider_service(request_client,
                       spider_class,
                       parse_strategy_factory,
                       crawling_strategy_factory,
                       aqi_model):
    spider_service = WeatherSpiderService(request_client=request_client,
                                          spider_class=spider_class,
                                          parse_strategy_factory=parse_strategy_factory,
                                          crawling_strategy_factory=crawling_strategy_factory,
                                          result_db_model=aqi_model)
    return spider_service

@pytest.fixture
def async_scheduler(database):
    jobstores = {
        'default': MongoDBJobStore(client=database.delegate)
    }
    executors = {
        'default': AsyncIOExecutor()
    }
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    return AsyncIOScheduler(
        jobstores=jobstores, executors=executors,
        job_defaults=job_defaults, timezone=utc
    )

@pytest.fixture
def job_service(async_scheduler):
    return AsyncJobService(async_scheduler=async_scheduler)
    

@pytest.mark.asyncio
async def test_get_spec(weather_spec, aqi_spec, news_spec, covid_spec):
    debug(weather_spec)
    assert (weather_spec is not None and
            weather_spec.job_type == 'weather_report')
    
    debug(aqi_spec)
    assert (aqi_spec is not None and 
            aqi_spec.job_type == "air_quality")
    
    debug(news_spec)
    assert (news_spec is not None and
            news_spec.job_type == "baidu_news_scraping")
    
    debug(covid_spec)
    assert (covid_spec is not None and 
            covid_spec.job_type == "baidu_covid_report")
