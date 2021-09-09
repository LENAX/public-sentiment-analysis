import re
import asyncio
from functools import partial
from datetime import datetime
from typing import List, Callable, Union
from concurrent.futures import ProcessPoolExecutor
from ...common.service.base_services import BaseSpiderService
from ...common.models.data_models import CrawlResult
from ...common.models.request_models import ScrapeRules, ParseRule
from ...common.models.db_models import Weather, AirQualityDBModel
from ...common.core import (BaseSpider, ParserContextFactory,
    BaseRequestClient, CrawlerContextFactory)
from ...common.utils import throttled
from itertools import chain
import logging
from logging import Logger, getLogger
import traceback

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)



class AQISpiderService(BaseSpiderService):
    """ A spider for crawling aqi reports
    
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 crawling_strategy_factory: CrawlerContextFactory,
                 result_db_model: Union[Weather, AirQualityDBModel],
                 crawl_method: str = 'bfs_crawler',
                 link_finder: str = 'link_parser',
                 coroutine_runner: Callable = asyncio.gather,
                 event_loop_getter: Callable = asyncio.get_event_loop,
                 process_pool_executor = ProcessPoolExecutor,
                 throttled_fetch: Callable = throttled,
                 max_retry: int = 5,
                 logger: Logger = spider_service_logger,
                 **kwargs) -> None:
        self._request_client = request_client
        self._spider_class = spider_class
        self._parse_strategy_factory = parse_strategy_factory
        self._crawler_context = crawling_strategy_factory.create(
            crawl_method, spider_class=spider_class,
            request_client=request_client,
            start_url='',
            max_retry=max_retry,
            parser_context=parse_strategy_factory.create(
                parser_name=link_finder, base_url='')
        )
        self._result_db_model = result_db_model
        self._max_retry = max_retry
        self._coroutine_runner = coroutine_runner
        self._event_loop_getter = event_loop_getter
        self._process_pool_executor = process_pool_executor
        self._throttled_fetch = throttled_fetch
        self._logger = logger

    def _required_fields_included(self,
                                  rules: List[ParseRule],
                                  fields_to_include: List[str]):
        fields_provided = set([rule.field_name for rule in rules])
        for required_field in fields_to_include:
            if required_field not in fields_provided:
                return False

        return True

    def _get_weather_page_classifier(
        self,
        weather_page_url_pattern: re.Pattern = re.compile(r"\/lishi\/(\w+)\/month\/(\w+).html|\/aqi\/(\w+)-\d{6}.html"),
        partial: Callable = partial
    ) -> Callable:
        def filter_result_by_pattern(node: CrawlResult, pattern: re.Pattern):
            return len(pattern.findall(node.url)) > 0
        return partial(filter_result_by_pattern, pattern=weather_page_url_pattern)

    def _get_location_filter(self,
                             location_names: List[str],
                             pattern_compiler: Callable = re.compile,
                             partial: Callable = partial) -> Callable:
        def location_filter(url: str, pattern: re.Pattern):
            return len(pattern.findall(url)) > 0

        location_pattern = pattern_compiler("|".join(location_names))
        return partial(location_filter, pattern=location_pattern)

    def _get_time_range_filter(self, start_time: datetime, end_time: datetime,
                               datetime_class: datetime = datetime,
                               pattern_compiler: Callable = re.compile,
                               partial: Callable = partial) -> Callable:
        def time_range_filter(url: str, start_time: datetime, end_time: datetime,
                              datetime_pattern: str,
                              re=re,
                              datetime_class: datetime = datetime) -> bool:
            # extract date from url
            date_str = re.findall(datetime_pattern, url)
            if len(date_str) and len(date_str[0]) == 6:
                url_date = datetime_class(
                    int(date_str[0][:4]), int(date_str[0][-2:]), 1)
                return start_time <= url_date <= end_time
            elif len(date_str) and len(date_str[0]) == 8:
                url_date = datetime_class(
                    int(date_str[0][:4]), int(date_str[0][4:6]), int(date_str[0][-2:]))
                return start_time <= url_date <= end_time
            return False

        return partial(time_range_filter,
                       start_time=start_time,
                       end_time=end_time,
                       datetime_class=datetime_class,
                       datetime_pattern='\d{6,8}')

    async def crawl(self,
                    urls: List[str],
                    rules: ScrapeRules,
                    compile: Callable = re.compile,
                    chain: Callable = chain) -> None:
        """ Crawls weather report site in the given manner
        
        This spider expects users to provide city names to scrape weather
        of some areas. If location code is not provided, then it will scrape weather
        data of all locations. The location code should be filled in the keywords field.

        This spider also expects users to provide a time range. If not provided, it will
        crawl all the weather reports.

        Users will provide two pipelines:
        1. Location filter pipeline for finding weather page links of specific locations
        2. Weather page pipeline for parsing weather information
            - required fields:
                - province
                - city
                - title
        
        """
        # validate parameters
        assert len(urls) > 0
        assert (
            len(rules.parsing_pipeline) >= 2 and
            len(rules.parsing_pipeline[0].parse_rules) > 0 and
            len(rules.parsing_pipeline[1].parse_rules) > 0)

        assert self._required_fields_included(
            rules=list(
                chain(*[rule.parse_rules for rule in rules.parsing_pipeline])),
            fields_to_include=['province', 'city'])

        self._logger.info("Parameters are validated. Prepare crawling...")

        self._crawler_context.start_url = urls[0]

        result_filter = self._get_weather_page_classifier()

        if rules.url_patterns and len(rules.url_patterns) > 0:
            pattern = compile(rules.url_patterns[0])
            result_filter = self._get_weather_page_classifier(
                weather_page_url_pattern=pattern)

        location_filter = self._get_location_filter(
            location_names=rules.keywords.include)
        time_range_filter = self._get_time_range_filter(
            start_time=rules.time_range.start_date,
            end_time=rules.time_range.end_date
        )

        self._logger.info("Start crawling...")
        
        _, aqi_home_page = await (self._spider_class(
            request_client=self._request_client, max_retry=rules.max_retry).fetch(urls[0]))
        province_parser = self._parse_strategy_factory.create(
            rules.parsing_pipeline[2].parser)
        province_parse_results = province_parser.parse(
            aqi_home_page, rules.parsing_pipeline[2].parse_rules)

        weather_pages = await self._crawler_context.crawl(
            rules=rules.parsing_pipeline[0].parse_rules,
            url_filter_functions=[
                location_filter,
                time_range_filter
            ],
            max_depth=rules.max_depth,
            result_filter_func=result_filter
        )

        self._logger.info(
            f"Crawl completed. Fetched {len(weather_pages)} results.")
        
        if len(weather_pages) == 0:
            self._logger.error(
                f"Fetched {len(weather_pages)} results from target site.")
            return

        
        self._logger.info(f"Start parsing results...")

        parsed_weather_history = []
        pipeline = rules.parsing_pipeline[1]
        
        weather_parser = self._parse_strategy_factory.create(pipeline.parser)
        for weather_page in weather_pages:
            page_text = weather_page.page_src
            parsed_results = weather_parser.parse(
                page_text, rules=pipeline.parse_rules)
            
            if len(parsed_results) == 0:
                self._logger.error(
                    f"parser generated empty result. input length: {len(page_text)}")
                continue
            
            weather_table_title = parsed_results[0]
            province = province_parse_results[0].value['province'].value if len(
                province_parse_results) > 0 else ""
            city = weather_table_title.value['city'].value
            for row in parsed_results[1:]:
                row_values = row.value
                row_values['province'].value = province
                row_values['city'].value = city

                for parsed_result in row_values.values():
                    parsed_result.value = parsed_result.value.replace("\r\n ", "").replace(" ", "")

            for daily_weather in parsed_results[1:]:
                try:
                    weather_record = self._result_db_model.parse_obj(daily_weather.value_to_dict())
                    parsed_weather_history.append(weather_record)
                    self._logger.debug(f"{weather_record}")
                except Exception as e:
                    traceback.print_exc()
                    self._logger.error(f"Unabled to parse {daily_weather}, {e}")
                

        await self._result_db_model.insert_many(parsed_weather_history)
        self._logger.info("Crawl completed!")


if __name__ == "__main__":
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    from ...common.models.request_models import (
        ScrapeRules, ParsingPipeline, ParseRule, KeywordRules, TimeRange
    )
    from ...common.core import (
        RequestClient, Spider
    )
    from typing import Any
    from ...common.core import (
        BaseSpider, ParserContextFactory, AsyncBrowserRequestClient, CrawlerContextFactory)
    from ...common.models.data_models import RequestHeader, AirQuality
    from ...common.models.db_models import AirQualityDBModel
    from yaml import load, dump
    from yaml import CLoader as Loader, CDumper as Dumper
    from os import getcwd
    from dateutil import parser
    from devtools import debug

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
                                   test_urls,
                                   rules):
        db = db_client[db_name]
        result_model_class.db = db

        async with (await client_session_class(headers=headers, cookies=cookies)) as client_session:
            spider_service = spider_service_class(request_client=client_session,
                                                  spider_class=spider_class,
                                                  parse_strategy_factory=parse_strategy_factory,
                                                  crawling_strategy_factory=crawling_strategy_factory,
                                                  result_db_model=result_model_class)
            await spider_service.crawl(test_urls, rules)

    cookie_text = """
    bdshare_firstime=1623405509618; ASP.NET_SessionId=u2sg3meispmmno45kzyeqj45; Hm_lvt_f48cedd6a69101030e93d4ef60f48fd0=1628646871; __51cke__=; __tins__4560568=%7B%22sid%22%3A%201630387994872%2C%20%22vd%22%3A%201%2C%20%22expires%22%3A%201630389794872%7D; __51laig__=3; __gads=ID=7737e4efcb77dae9-22af63ae8dcb004d:T=1631080420:RT=1631080420:S=ALNI_MZJU6nWegxpgYwNaH7Sh3aQUKN4CA; Hm_lpvt_f48cedd6a69101030e93d4ef60f48fd0=1631152954
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
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    )
    use_db = 'test'
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name=use_db)
    urls = [
        "http://www.tianqihoubao.com/aqi/"
    ]
    print(urls)
    config = ScrapeRules(
        keywords=KeywordRules(
            # include=[
            #     "wuhan", "shiyan", "yichang", "ezhou", "jinmeng", "xiaogan",
            #     "huanggang", 'xianning', "huangshi", 'enshi', 'suizhou', 'jinzhou'
            # ],
            include=[
                "wuhan"
            ]
        ),
        max_concurrency=500,
        max_depth=1,
        max_retry=5,
        time_range=TimeRange(
            start_date=parser.parse('2021-08-01'),
            end_date=parser.parse('2021-09-01')
        ),
        parsing_pipeline=[
            ParsingPipeline(
                name="aqi_link_finder",
                parser='link_parser',
                parse_rules=[
                    ParseRule(
                        field_name='city_link',
                        rule="//*[@id='content']/div[2]/dl[15]/dd/a|//*[@id='bd']/div[1]/div[3]/ul/li/a",
                        rule_type='xpath',
                        slice_str=[7, 23]
                    )
                ]
            ), ParsingPipeline(
                name='aqi_parser',
                parser='list_item_parser',
                parse_rules=[
                    ParseRule(
                        field_name='province',
                        rule="//*[@id='mnav']/div[1]/a[3]/text()",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='city',
                        rule="//*[@id='content']/h1",
                        rule_type='xpath',
                        slice_str=[7, 9]
                    ), ParseRule(
                        field_name='date',
                        rule=" //tr/td[1]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='quality',
                        rule="//tr/td[2]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='aqi',
                        rule="//tr/td[3]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='aqi_rank',
                        rule="//tr/td[4]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='pm25',
                        rule="//tr/td[5]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='pm10',
                        rule="//tr/td[6]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='so2',
                        rule="//tr/td[7]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='no2',
                        rule="//tr/td[8]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='co',
                        rule="//tr/td[9]",
                        rule_type='xpath'
                    ), ParseRule(
                        field_name='o3',
                        rule="//tr/td[10]",
                        rule_type='xpath'
                    )
                ]), ParsingPipeline(
                    name="province_parser",
                    parser='list_item_parser',
                    parse_rules=[
                        ParseRule(
                            field_name='province',
                            rule="//*[@id='content']/div[2]/dl[15]/dt/b/text()",
                            rule_type='xpath'
                        )
                    ]
            )]
    )

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
        spider_service_class=AQISpiderService,
        result_model_class=AirQualityDBModel,
        test_urls=urls,
        rules=config
    ))
