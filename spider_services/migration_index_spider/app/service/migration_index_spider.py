import re
import json
import asyncio
import aiohttp
from typing import Any
from functools import partial
from datetime import datetime
from pymongo import InsertOne, DeleteMany, ReplaceOne, UpdateOne
from typing import List, Callable, Union
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor
from ....common.service.base_services import BaseSpiderService
from ....common.models.data_models import Location, MigrationIndex

from ....common.models.request_models import ScrapeRules, ParseRule
from ....common.models.db_models import MigrationIndexDBModel
from ....common.core import (
    BaseSpider, ParserContextFactory, AsyncBrowserRequestClient, CrawlerContextFactory)
from ....common.utils import throttled
import traceback
import logging
from logging import Logger, getLogger
from dateutil import parser
from devtools import debug

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)


class MigrationIndexSpiderService(BaseSpiderService):
    """ A spider for crawling weather forecasts
    
    """

    def __init__(self,
                 request_client: AsyncBrowserRequestClient,
                 spider_class: BaseSpider,
                 result_db_model: MigrationIndexDBModel,
                 result_data_model: MigrationIndex,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = spider_service_logger,
                 **kwargs) -> None:
        self._request_client = request_client
        self._spider_class = spider_class
        self._result_db_model = result_db_model
        self._result_data_model = result_data_model
        self._throttled_fetch = throttled_fetch
        self._logger = logger
    
    

    async def crawl(self, urls: List[str], rules: ScrapeRules):
        self._logger.info("Start crawling...")
        


if __name__ == "__main__":
    import asyncio
    from typing import Any
    from motor.motor_asyncio import AsyncIOMotorClient
    from ....common.models.request_models import (
        ScrapeRules, ParsingPipeline, ParseRule, KeywordRules, TimeRange,
    )
    from ....common.models.data_models import RequestHeader
    from ....common.models.db_models import MigrationIndexDBModel
    from ....common.core import Spider
    from yaml import load, dump
    from yaml import CLoader as Loader, CDumper as Dumper
    from os import getcwd
    from devtools import debug
    import aiohttp
    import cProfile

    def create_client(host: str, username: str,
                      password: str, port: int,
                      db_name: str) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin")

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

    def save_config(config, path, dump: Any = dump, dump_class: Any = Dumper):
        with open(path, 'w+') as f:
            config_text = dump(config, Dumper=dump_class)
            f.write(config_text)

    async def test_spider_services(db_client,
                                   db_name,
                                   headers,
                                   cookies,
                                   client_session_class,
                                   spider_class,
                                   parse_strategy_factory,
                                   crawling_strategy_factory,
                                   spider_service_class,
                                   result_model_class,
                                   result_data_model,
                                   test_urls,
                                   rules):
        db = db_client[db_name]
        result_model_class.db = db
        # html_model_class.db = db

        async with (await client_session_class(headers=headers, cookies=cookies)) as client_session:
            spider_service = spider_service_class(request_client=client_session,
                                                  spider_class=spider_class,
                                                  parse_strategy_factory=parse_strategy_factory,
                                                  crawling_strategy_factory=crawling_strategy_factory,
                                                  result_db_model=result_model_class,
                                                  result_data_model=result_data_model)
            await spider_service.crawl(test_urls, rules)

    cookie_text = """BIDUPSID=C2730507E1C86942858719FD87A61E58;
    PSTM=1591763607; BAIDUID=0145D8794827C0813A767D21ADED26B4:FG=1;
    BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek;
    __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BD_UPN=123253; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5;
    H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP;
    """
    cookie_strings = cookie_text.replace("\n", "").replace(" ", "").split(";")
    cookies = {}
    for cookie_str in cookie_strings:
        try:
            key, value = cookie_str.split("=")
            cookies[key] = value
        except IndexError:
            print(cookie_str)
        except ValueError:
            print(cookie_str)

    headers = RequestHeader(
        accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    )
    use_db = 'test'
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name=use_db)
    urls = [
        "https://weather.cma.cn/"
    ]
    config = ScrapeRules(
        max_concurrency=1000,
        max_retry=10,
        parsing_pipeline=[
            ParsingPipeline(
                name="update_time_parser",
                parser='list_item_parser',
                parse_rules=[
                    ParseRule(
                        field_name='lastUpdate',
                        rule="/html/body/div[1]/div[2]/div[1]/div[1]/div[1]/text()",
                        rule_type='xpath',
                        slice_str=[7, 23]
                    )
                ]
            ), ParsingPipeline(
                name='daily_forecast_parser',
                parser='list_item_parser',
                parse_rules=[
                    ParseRule(
                        field_name='day',
                        rule="//*[@id='dayList']/div/div[1]/text()[1]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='day',
                        rule="//*[@id='dayList']/div[*]/div[1]/text()[1]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='date',
                        rule="//*[@id='dayList']/div/div[1]/text()[2]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='morningWeather',
                        rule="//*[@id='dayList']/div/div[3]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='morningWindDirection',
                        rule="//*[@id='dayList']/div/div[4]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='morningWindScale',
                        rule="//*[@id='dayList']/div/div[5]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='highestTemperature',
                        rule="//*[@id='dayList']/div/div[6]/div/div[1]/text()",
                        rule_type='xpath',
                        slice_str=[0, -1]
                    ), ParseRule(
                        field_name='lowestTemperature',
                        rule="//*[@id='dayList']/div/div[6]/div/div[2]/text()",
                        rule_type='xpath',
                        slice_str=[0, -1]
                    ), ParseRule(
                        field_name='eveningWeather',
                        rule="//*[@id='dayList']/div/div[8]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='eveningWindDirection',
                        rule="//*[@id='dayList']/div/div[9]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='eveningWindScale',
                        rule="//*[@id='dayList']/div/div[10]",
                        rule_type='xpath'
                    ),
            ]), ParsingPipeline(
                name='hourly_forecast_parser',
                parser='list_item_parser',
                parse_rules=[ParseRule(
                    field_name='time',
                    rule="//tr[1]/td[position()>1]/text()",
                    rule_type='xpath'
                ), ParseRule(
                    field_name='weather',
                    rule="//tr[2]/td/img/@src",
                    rule_type='xpath',
                    slice_str=[-5, -4]
                ), ParseRule(
                    field_name='temperature',
                    rule="//tr[3]/td[position() > 1]/text()",
                    rule_type='xpath',
                    slice_str=[0, -1]
                ), ParseRule(
                    field_name='precipitation',
                    rule="//tr[4]/td[position() >1]/text()",
                    rule_type='xpath'
                ), ParseRule(
                    field_name='windSpeed',
                    rule="//tr[5]/td[position() >1]/text()",
                    rule_type='xpath',
                    slice_str=[0, -3]
                ), ParseRule(
                    field_name='windDirection',
                    rule="//tr[6]/td[position() >1]/text()",
                    rule_type='xpath'
                ), ParseRule(
                    field_name='pressure',
                    rule="//tr[7]/td[position() >1]/text()",
                    rule_type='xpath',
                    slice_str=[0, -3]
                ), ParseRule(
                    field_name='humidity',
                    rule="//tr[8]/td[position() >1]/text()",
                    rule_type='xpath',
                    slice_str=[0, -1]
                ), ParseRule(
                    field_name='cloud',
                    rule="//tr[9]/td[position() >1]/text()",
                    rule_type='xpath',
                    slice_str=[0, -1]
                )]
        )]
    )
    
    # save_config(config, './spider_services/service_configs/cma_weather.yml')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider_services(
        db_client=db_client,
        db_name=use_db,
        headers=headers.dict(),
        cookies=cookies,
        client_session_class=AsyncBrowserRequestClient,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        spider_service_class=MigrationIndexSpiderService,
        result_model_class=MigrationIndexDBModel,
        result_data_model=MigrationIndex,
        test_urls=urls,
        rules=config
    ))
