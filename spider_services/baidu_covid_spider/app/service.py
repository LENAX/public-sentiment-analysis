import re
import asyncio
from typing import List, Any, Tuple, Callable, TypeVar, Union
from concurrent.futures import ProcessPoolExecutor
from ...common.service.base_services import BaseSpiderService
from ...common.models.request_models import ScrapeRules, ParseRule
from ...common.models.db_models import BaiduCOVIDReport
from ...common.core import (
    BaseSpider, ParserContextFactory, BaseRequestClient)
from ...common.utils import throttled
from itertools import chain
import logging
from logging import Logger, getLogger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)



class BaiduCOVIDSpider(BaseSpiderService):
    """ A spider for crawling COVID-19 reports from Baidu
    
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 result_db_model: BaiduCOVIDReport,
                 coroutine_runner: Callable = asyncio.gather,
                 event_loop_getter: Callable = asyncio.get_event_loop,
                 process_pool_executor: ProcessPoolExecutorClass = ProcessPoolExecutor,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = getLogger(f"{__name__}.BaiduCOVIDSpider"),
                 **kwargs) -> None:
        self._request_client = request_client
        self._spider_class = spider_class
        self._parse_strategy_factory = parse_strategy_factory
        self._result_db_model = result_db_model
        self._coroutine_runner = coroutine_runner
        self._event_loop_getter = event_loop_getter
        self._process_pool_executor = process_pool_executor
        self._throttled_fetch = throttled_fetch
        self._logger = logger
        self._create_report_classifier()

    def _required_fields_included(self, 
                                  rules: List[ParseRule],
                                  fields_to_include: List[str]):
        fields_provided = set([rule.field_name for rule in rules])
        for required_field in fields_to_include:
            if required_field not in fields_provided:
                return False
        
        return True

    def _create_report_classifier(self, pattern_compiler: Callable = re.compile):
        self._classifier = {
            pattern_compiler("#tab4"): 'world',
            pattern_compiler("国内各地区疫情统计汇总"): 'domestic',
            pattern_compiler("病死率"): 'foreign_country',
            pattern_compiler("国外疫情"): 'world',
            pattern_compiler("市|区"): 'domestic_city',
        }

    def _classify_report_type(self, url: str, page_text: str):
        """ Guess report type for page text """
        for report_pattern in self._classifier:
            if report_pattern.search(url) or report_pattern.search(page_text):
                return self._classifier[report_pattern]
        return 'domestic'

    async def crawl(self, 
                    urls: List[str],
                    rules: ScrapeRules,
                    city_param_pattern: re.Pattern = re.compile("[\u4e00-\u9fa5]{1,}-[\u4e00-\u9fa5]{1,}"),
                    chain: Callable = chain
                    ) -> None:
        """ Crawl search results within given rules like time range, keywords, and etc.
        
        User will provide the search page url of Baidu COVID-19 report 
        (https://voice.baidu.com/act/newpneumonia/newpneumonia) and areas to view.

        City format: (Country|Province)-(Country|City)
        For example: 美国-美国, 广东-深圳
        Ill-formatted cities will be ignored.

        The parsed report should at least have the following fields:
        1. city (if it is empty then it is assumed to be a national report)
        2. nation
        3. last_update

        This spider will have 4 pipelines due to different web page structures:
        1. domestic report pipeline (pipeline_name: domestic)
        2. domestic_city report pipeline (pipeline_name: domestic_city)
        3. world report pipeline  (pipeline_name: world)
        4. foreign countries' reports pipeline (pipeline_name: foreign_country)

        Args:
            urls: baidu news url
            rules: 
                - rules the spider should follow. This mode expects keywords from users.
                - if keyword is not provided, the spider will return a national report
        """
        # make sure user has provide the covid report url
        assert len(urls) > 0

        # make sure user has provide at least one parsing pipeline
        assert len(rules.parsing_pipeline) > 0

        # make sure user has provided the required pipelines
        assert self._required_fields_included(
            list(chain(*[rule.parse_rules for rule in rules.parsing_pipeline])),
            ['domestic_city', 'last_update', 'world', 'domestic', 'foreign_country'])
        
        self._logger.info("Parameters are validated. Prepare crawling...")

        # use the first one as base url and ignore the rest
        base_url = urls[0]
        covid_report_urls = [base_url, f"{base_url}#tab4"]
        
        # get cities from rules
        cities = rules.keywords.include

        if len(cities):
            covid_report_urls += [f"{base_url}?city={city}" 
                                  for city in cities
                                  if city_param_pattern.match(city)]
        
        self._logger.info("Start crawling...")

        # create spiders from urls
        report_spiders = self._spider_class.create_from_urls(covid_report_urls, self._request_client)
        
        # fetch report pages
        report_pages = await self._throttled_fetch(
            max_concurrency=rules.max_concurrency,
            tasks=[spider.fetch() for spider in report_spiders])
        
        self._logger.info(f"Crawl completed. Fetched {len(report_pages)} results.")
        self._logger.info(f"Start parsing results...")

        # create report parser and parse report
        parsed_reports = []
        parsing_pipelines = {
            pipeline.parse_rules[0].field_name: pipeline
            for pipeline in rules.parsing_pipeline
        }
        # create parser by guessing its type
        for i, page in enumerate(report_pages):
            self._logger.info(f"Parsing {i}/{len(report_pages)} pages")
            url, raw_page = page
            report_type = self._classify_report_type(url, raw_page)
            pipeline = parsing_pipelines[report_type]
            parser = self._parse_strategy_factory.create(pipeline.parser)
            parsed_result = parser.parse(raw_page, rules=pipeline.parse_rules)[0]
            result_dict = parsed_result.value_to_dict()
            covid_report_summary = self._result_db_model.parse_obj(result_dict)
            covid_report_summary.report_type = result_dict[report_type]
            self._logger.debug(f"transformed model: {covid_report_summary}")
            parsed_reports.append(covid_report_summary)

        # save reports to db
        await self._result_db_model.insert_many(parsed_reports)
        self._logger.info("Done!")


