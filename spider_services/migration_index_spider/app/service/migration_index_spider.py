import re
import ujson
import asyncio
import aiohttp
from typing import Any, Tuple
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
    BaseSpider, ParserContextFactory, AsyncBrowserRequestClient, RequestClient, CrawlerContextFactory)
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

    def _get_migration_index_urls(self, base_url: str, area_codes: List[str],
                                  migration_type: str, date: datetime = datetime.now()):
        return [f"{base_url}?dt=province&id={area_code}&type={migration_type}&date={date.strftime('%Y%m%d')}"
                for area_code, _ in area_codes]
        
    def _parse_jsonp(self, jsonp_str: str) -> dict:
        try:
            if len(jsonp_str) == 0:
                self._logger.error("Expected jsonp string to be a non-empty string!")
                return {}
            
            json_data = ujson.loads(jsonp_str)
            return json_data
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return {}
            
    def _is_valid_response_data(self, response: dict):
        return all([
            'errno' in response and response['errno'] == 0,
            ('data' in response and 'list' in response['data'] and 
             type(response['data']['list']) is dict and
             len(response['data']['list']) > 0)])
            
    def _to_migration_index(self, data: dict, areaCode: str, migration_type: str) -> List[MigrationIndex]:
        """ Convert json to list of migration index data

        Args:
            data (dict): response from json, must contain field data and data.list
            areaCode (str): area code of the migration data
            migration_type (str): is either 'move_in' or 'move_out'
        Returns:
            List[MigrationIndex]: converted data
        """
        try:
            if not self._is_valid_response_data(data):
                self._logger.error(f'Invalid response data: {data}')
                return []
            
            migration_indexes = [
                self._result_data_model(
                    areaCode=areaCode,
                    date=date,
                    migration_type=migration_type,
                    migration_index=migration_index_value)
                for date, migration_index_value in data['data']['list'].items()]

            return migration_indexes
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return []
        
    def _url_to_area_code(self, url: str) -> str:
        if type(url) is not str:
            self._logger.error(f"Expected url {url} to be a string!")
            return ""
        
        try:
            query_arg_list = url.split("&")
            
            if len(query_arg_list) < 2:
                self._logger.error(f"Expected url {url} to contain at least two query arguments!")
                return ""
            
            areaCode_arg = [arg for arg in query_arg_list if arg.startswith('id=')]
            
            if len(areaCode_arg) != 1:
                self._logger.error(f"Expected areaCode_arg {areaCode_arg} to have exactly one match!")
                return ""
            
            return areaCode_arg[0][3:]
            
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return ""
        
    def _parse_migration_api_response(self, responses: List[Tuple[str, str]], migration_type: str) -> List[MigrationIndex]:
        """Parse response data from migration index api and convert them to MigrationIndex objects. 

        Args:
            responses (List[Tuple[str, str]]): response string from migration index api
            migration_type (str): is either 'move_in' or 'move_out'

        Returns:
            List[MigrationIndex]: list of MigrationIndex objects
        """
        try:
            migration_data = []
            
            for response in responses:
                url, resp_data = response
                areaCode = self._url_to_area_code(url)
                parsed_response = self._parse_jsonp(resp_data)
                migration_indexes = self._to_migration_index(parsed_response, areaCode, migration_type)
                migration_data.extend(migration_indexes)
            
            return migration_data
        
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return []
        
    async def _crawl_migration_indexes(self, base_url: str, area_codes: List[str], migration_type: str, max_retry: int, max_concurrency: int) -> List[MigrationIndex]:
        try:
            data_urls = self._get_migration_index_urls(base_url, area_codes, migration_type)
            spiders = self._spider_class.create_from_urls(
                data_urls, self._request_client, max_retry)
            migration_api_responses = await self._throttled_fetch(max_concurrency, [spider.fetch() for spider in spiders])
            migration_indexes = self._parse_migration_api_response(migration_api_responses, migration_type)
            return migration_indexes
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return []
          
    async def crawl(self, urls: List[str], rules: ScrapeRules):
        try:
            if len(urls) == 0 or rules is None:
                self._logger.error("No url or rules are specified.")
                return
            
            self._logger.info("Start crawling...")
            base_url = urls[0]
            areaCodes = rules.keywords.include
            move_in_indexes, move_out_indexes = await self._throttled_fetch(
                rules.max_concurrency, [
                    self._crawl_migration_indexes(base_url, areaCodes, 'move_in', rules.max_retry, rules.max_concurrency),
                    self._crawl_migration_indexes(base_url, areaCodes, 'move_out', rules.max_retry, rules.max_concurrency)
                ])
            migration_indexes = move_in_indexes + move_out_indexes
            migration_indexes_db_objects = self._result_db_model.parse_many(migration_indexes)
            await self._result_db_model.insert_many(migration_indexes_db_objects)
            self._logger.info("Done!")
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
        


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
    import ujson

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

    def get_area_codes(data_path):
        city_area_codes = []
        
        with open(data_path, 'r') as f:
            area_code_data = ujson.loads(f.read())
            
        for area in area_code_data:
            cities = area['children']
            province_name = area['name']
            
            for city in cities:
                # city_name = f"{province_name}{city['name']}"
                code = city['code'] if len(city['code']) == 6 else f"{city['code']}00"
                city_area_codes.append(code)
        
        return city_area_codes

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
        "https://huiyan.baidu.com/migration/historycurve.json"
    ]
    city_area_codes = get_area_codes(f"{getcwd()}/spider_services/migration_index_spider/app/service_configs/pc-code.json")
    print(city_area_codes)
    config = ScrapeRules(
        max_concurrency=100,
        max_retry=10,
        keywords=KeywordRules(
            include=city_area_codes
        )
    )
    
    # save_config(config, './spider_services/service_configs/cma_weather.yml')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider_services(
        db_client=db_client,
        db_name=use_db,
        headers=headers.dict(),
        cookies=cookies,
        client_session_class=RequestClient,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        spider_service_class=MigrationIndexSpiderService,
        result_model_class=MigrationIndexDBModel,
        result_data_model=MigrationIndex,
        test_urls=urls,
        rules=config
    ))
