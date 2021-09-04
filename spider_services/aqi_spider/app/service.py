import re
import asyncio
from functools import partial
from datetime import datetime
from typing import List, Any, Callable, Union
from concurrent.futures import ProcessPoolExecutor
from ...common.service.base_services import BaseSpiderService
from ...common.models.data_models import CrawlResult
from ...common.models.request_models import ScrapeRules, ParseRule
from ...common.models.db_models import Weather, AirQuality
from ...common.core import (
    BaseSpider, ParserContextFactory,
    BaseRequestClient, CrawlerContextFactory)
from ...common.utils import throttled
from itertools import chain
import logging
from logging import Logger, getLogger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)

class WeatherSpiderService(BaseSpiderService):
    """ A spider for crawling historical weather reports
    
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 crawling_strategy_factory: CrawlerContextFactory,
                 result_db_model: Union[Weather, AirQuality],
                 crawl_method: str = 'bfs_crawler',
                 link_finder: str = 'link_parser',
                 coroutine_runner: Callable = asyncio.gather,
                 event_loop_getter: Callable = asyncio.get_event_loop,
                 process_pool_executor=ProcessPoolExecutor,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = getLogger(f"{__name__}.WeatherSpiderService"),
                 **kwargs) -> None:
        self._request_client = request_client
        self._spider_class = spider_class
        self._parse_strategy_factory = parse_strategy_factory
        self._crawler_context = crawling_strategy_factory.create(
            crawl_method, spider_class=spider_class,
            request_client=request_client,
            start_url='',
            parser_context=parse_strategy_factory.create(
                parser_name=link_finder, base_url='')
        )
        self._result_db_model = result_db_model

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
        weather_page_url_pattern: re.Pattern = re.compile("\/lishi\/(\w+)\/month\/(\w+).html"),
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
        self._logger.info(f"Start parsing results...")

        parsed_weather_history = []
        pipeline = rules.parsing_pipeline[1]
        weather_parser = self._parse_strategy_factory.create(pipeline.parser)
        for weather_page in weather_pages:
            page_text = weather_page.page_src
            parsed_results = weather_parser.parse(
                page_text, rules=pipeline.parse_rules)

            weather_table_title = parsed_results[0]
            title = weather_table_title.value['title'].value
            province = weather_table_title.value['province'].value
            city = weather_table_title.value['city'].value
            for row in parsed_results[1:]:
                row_values = row.value
                row_values['title'].value = title
                row_values['province'].value = province
                row_values['city'].value = city

                for parsed_result in row_values.values():
                    parsed_result.value = parsed_result.value.replace(
                        "\r\n ", "").replace(" ", "")

            for daily_weather in parsed_results[1:]:
                self._logger.debug(f"Untransformed object: {daily_weather}")
                # result_dict = {key: daily_weather.value[key].value for key in daily_weather.value}
                weather_record = self._result_db_model.parse_obj(
                    daily_weather.value_to_dict())
                self._logger.debug(f"transformed model: {weather_record}")
                parsed_weather_history.append(weather_record)

        await self._result_db_model.insert_many(parsed_weather_history)
        self._logger.info("Crawl complete!")
