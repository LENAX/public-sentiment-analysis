import re
import asyncio
from uuid import uuid5, NAMESPACE_OID
from functools import partial
from datetime import datetime, timedelta
from typing import List, Any, Tuple, Callable, TypeVar, Union
from motor.motor_asyncio import AsyncIOMotorDatabase
from concurrent.futures import ProcessPoolExecutor
from .base_services import BaseSpiderService, BaseServiceFactory
from ..models.data_models import (
    RequestHeader,
    HTMLData,
    CrawlResult
)
from ..models.request_models import ScrapeRules, ParseRule
from ..models.db_models import (
    Result, Weather, AirQuality, COVIDReport, News
)
from ..enums import JobType
from ..core import (
    BaseSpider, ParserContextFactory,
    BaseRequestClient, AsyncBrowserRequestClient, RequestClient,
    CrawlerContextFactory
)
from ..utils import throttled
from itertools import chain
import logging
from logging import Logger, getLogger

logging.basicConfig()
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)

""" Defines all spider services

Catalog
1. HTMLSpiderService
    - Scrape static web page and return its content

"""
SemaphoreClass = TypeVar("SemaphoreClass")
EventLoop = TypeVar("EventLoop")
ProcessPoolExecutorClass = TypeVar("ProcessPoolExecutorClass")


class HTMLSpiderService(BaseSpiderService):

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 result_db_model: Result,
                 html_data_model: HTMLData,
                 coroutine_runner: Callable = asyncio.gather,
                 throttled_fetch: Callable = throttled,
                 **kwargs) -> None:
        self._request_client = request_client
        self._spider_class = spider_class
        self._parse_strategy_factory= parse_strategy_factory
        self._result_db_model = result_db_model
        self._html_data_model = html_data_model
        self._coroutine_runner = coroutine_runner
        self._throttled_fetch = throttled_fetch

    async def crawl(self, urls: List[str], rules: ScrapeRules) -> None:
        """ Get html data given the data source

        Args: 
            data_src: List[str]
            rules: ScrapeRules
        """
        # try create many spiders
        spiders = self._spider_class.create_from_urls(urls, self._request_client)

        html_pages = await self._throttled_fetch(
            rules.max_concurrency, *[spider.fetch() for spider in spiders])

        result_dt = datetime.now()
        html_data = [
            self._html_data_model(
                url=page[0], html=page[1], create_dt=result_dt)
            for page in html_pages
        ]
        result_name = f"result_{result_dt}"
        crawl_result = self._result_db_model(
            result_id=self._table_id_generator(result_name),
            name=result_name,
            description="",
            data=html_data,
            create_dt=result_dt
        )
        await crawl_result.save()



class BaiduNewsSpider(BaseSpiderService):
    """ A spider for crawling baidu news
    
    You can crawl search engine pages with this service if the result page has a paging parameter.
    Provide the paging parameter and the link result url pattern to crawl raw results.
    If extraction rules are provided, this service will try to extract information from raw results.
    
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 result_db_model: News,
                 coroutine_runner: Callable = asyncio.gather,
                 event_loop_getter: Callable = asyncio.get_event_loop,
                 process_pool_executor: ProcessPoolExecutorClass = ProcessPoolExecutor,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = getLogger(f"{__name__}.BaiduNewsSpider"),
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
        self._create_time_string_extractors()

    def _create_time_string_extractors(self):
        self._cn_time_string_extractors = {
            re.compile('\d{1,2}秒前'):
                lambda now, time_str: now -
                timedelta(seconds=int(re.search('\d+', time_str).group(0))),
            re.compile('\d{1,2}分钟前'):
                lambda now, time_str: now -
                timedelta(minutes=int(re.search('\d+', time_str).group(0))),
            re.compile('\d{1,2}小时前'):
                lambda now, time_str: now -
                timedelta(hours=int(re.search('\d+', time_str).group(0))),
            re.compile('\d{1,2}天前'):
                lambda now, time_str: now -
                timedelta(days=int(re.search('\d+', time_str).group(0))),
            re.compile('昨天\d{1,2}:\d{1,2}'):
                lambda now, time_str: datetime(
                    now.year, now.month, now.day-1,
                    int(re.findall('\d+', time_str)[0]),
                    int(re.findall('\d+', time_str)[1])
            ),
            re.compile('\d{1,2}月\d{1,2}日'):
                lambda now, time_str: datetime(
                    now.year,
                    int(re.findall('\d+', time_str)[0]),
                int(re.findall('\d+', time_str)[1])),

            re.compile('\d{1,2}年\d{1,2}月\d{1,2}日'):
                lambda now, time_str: datetime(
                    *(re.findall('\d+', time_str))
            )
        }

    def _standardize_datetime(self, time_str):
        """ Convert non standard format time string to standard datetime format
        
        Non standard cn time strings:
        1. 58分钟前
        2. 1小时前
        3. 昨天13:15
        4. 6月5日
        5. 5天前
        
        """
        today = datetime.now()
        converted = datetime(today.year, today.month, today.day)

        if len(time_str) == 0:
            return converted

        for pattern in self._cn_time_string_extractors:
            if pattern.match(time_str):
                converted = self._cn_time_string_extractors[pattern](
                    today, time_str)
                return converted

        return converted
    
    def _group_fields_by(self, columns: List[str]):
        pass

    async def crawl(self, urls: List[str], 
                    rules: ScrapeRules,
                    paging_param: str = "pn") -> None:
        """ Crawl search results within given rules like time range, keywords, and etc.
        
        User will provide the search page url of Baidu News (https://www.baidu.com/s?tn=news&ie=utf-8).
        This spider will automatically generate the actual search urls.

        Args:
            urls: baidu news url
            rules: rules the spider should follow. This mode expects keywords and size from users.
        """
        # if user provides no url, use default url
        spiders = []

        # require the user to provide url, max_pages and keywords
        assert (len(urls) > 0 and 
                type(rules.max_pages) is int and 
                len(rules.keywords.include) > 0)

        self._logger.info("Parameters are validated. Prepare crawling...")
        self._logger.info("Start crawling news...")

        # generate search page urls given keywords and page limit
        for search_base_url in urls:
            search_urls = [f"{search_base_url}&word={kw}&{paging_param}={page_number}"
                           for page_number in range(rules.max_pages)
                           for kw in rules.keywords.include]
            spiders.extend(self._spider_class.create_from_urls(search_urls, self._request_client))


        # concurrently fetch search results with a concurrency limit
        # TODO: could boost parallelism by running parsers at the same time
        search_result_pages = await self._throttled_fetch(
            rules.max_concurrency, [spider.fetch() for spider in spiders])

        self._logger.info(
            f"Crawl completed. Fetched {len(search_result_pages)} results.")
        self._logger.info(f"Start crawling news pages...")
        self._logger.info(f"Parsing news list...")
        # for now, the pipeline is fixed to the following
        # 1. extract all search result blocks from search result pages (title, href, abstract, date)
        # step 1 will produce a list of List[ParseResult], and have to assume the order to work correctly
        # collect search results from parser, which has the form ParseResult(name=item, value={'attribute': ParseResult(name='attribute', value='...')})
        parsed_search_result = []
        search_page_parser = self._parse_strategy_factory.create(
            rules.parsing_pipeline[0].parser)

        self._logger.info(f"Standardizing news' publish dates..")
        
        
        for _, raw_page in search_result_pages:
            search_results = search_page_parser.parse(
                raw_page, rules.parsing_pipeline[0].parse_rules)

            # standardize datetime
            for result in search_results:
                result_attributes = result.value
                if 'date' in result_attributes:
                    result_attributes['date'].value = self._standardize_datetime(
                        result_attributes['date'].value)

            parsed_search_result.extend(search_results)
        
        self._logger.info(f"News list is parsed.")
        self._logger.info(f"News' publish dates standardized.")
        
        # 2. if date is provided, parse date strings and include those pages within date range
        if (len(parsed_search_result) > 0 and rules.time_range):
            self._logger.info(f"Applying time filters")
            if rules.time_range.past_days:
                last_date = datetime.now() - timedelta(days=rules.time_range.past_days)
                parsed_search_result = [result for result in parsed_search_result
                                        if 'date' in result.value and result.value['date'].value >= last_date]
            elif rules.time_range.date_before and rules.time_range.date_after:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result.value and 
                                            rules.time_range.date_after <= result.value['date'].value < rules.time_range.date_before)]
            elif rules.time_range.date_before:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result.value and
                                            rules.time_range.date_after <= result.value['date'].value)]
            elif rules.time_range.date_before and rules.time_range.date_after:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result.value and
                                            result.value['date'].value < rules.time_range.date_before)]
                            
        # 3. if keyword exclude is provided, exclude all pages having those keywords
        if (len(parsed_search_result) > 0 and rules.keywords and rules.keywords.exclude):
            self._logger.info(f"Applying keyword filters...")
            exclude_kws = "|".join(rules.keywords.exclude)
            exclude_patterns = re.compile(f'^((?!{exclude_kws}).)*$')
            parsed_search_result = [result for result in parsed_search_result
                                    if ('abstract' in result.value and 
                                        'title' in result.value and 
                                        re.finditer(exclude_patterns, result.value['abstract']) and
                                        re.finditer(exclude_patterns, result.value['title']))]
        
        self._logger.info(
            f"Got {len(parsed_search_result)} after filtering...")
        self._logger.info(f"Start crawling news pages...")
        # 4. fetch remaining pages
        content_pages = []
        if (len(parsed_search_result) > 0):
            content_urls = [result.value['href'].value for result in parsed_search_result]
            content_spiders = self._spider_class.create_from_urls(content_urls, self._request_client)
            content_pages = await self._throttled_fetch(
                rules.max_concurrency, [spider.fetch() for spider in content_spiders])
        
            self._logger.info(f"Fetched {len(content_pages)} news pages")
        
        # 5. use the last pipeline and extract contents. (title, content, url)
        self._logger.info(f"Start parsing news pages")
        content_parser = self._parse_strategy_factory.create(
            rules.parsing_pipeline[1].parser)
        results = []
        
        for i, page in enumerate(content_pages):
            self._logger.info(f"parsing {i}/{len(content_pages)}")
            content_url, content_page = page
            if len(content_page) == 0:
                self._logger.error(f"failed to fetch url: {content_url}")
                continue
            
            parsed_contents = content_parser.parse(content_page, rules.parsing_pipeline[1].parse_rules)
            content_dict = {
                result.name: result.value for result in parsed_contents}
            news = self._result_db_model.parse_obj(content_dict)
            news.url = content_url
            results.append(news)
            
        # 6. finally save results to db
        if len(results) > 0:
            self._logger.info(f"Saving results...")
            await self._result_db_model.insert_many(results)
            self._logger.info("Done!")
        else:
            self._logger.info("No new results retrieved in this run...")


class BaiduCOVIDSpider(BaseSpiderService):
    """ A spider for crawling COVID-19 reports from Baidu
    
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 result_db_model: COVIDReport,
                 html_data_model: HTMLData,
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
        self._html_data_model = html_data_model
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
            # covid_report_summary = self._result_db_model(
            #     name=f"{parsed_result.value[report_type].value}实时疫情报告",
            #     description="新型冠状病毒肺炎疫情实时大数据报告",
            #     data=parsed_result.value.values(),
            #     create_dt=result_dt
            # )
            self._logger.debug(f"transformed model: {covid_report_summary}")
            parsed_reports.append(covid_report_summary)

        # save reports to db
        await self._result_db_model.insert_many(parsed_reports)
        self._logger.info("Done!")



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
                 process_pool_executor: ProcessPoolExecutorClass = ProcessPoolExecutor,
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
            rules=list(chain(*[rule.parse_rules for rule in rules.parsing_pipeline])),
            fields_to_include=['province', 'city'])
        
        self._logger.info("Parameters are validated. Prepare crawling...")

        self._crawler_context.start_url = urls[0]

        result_filter = self._get_weather_page_classifier()

        if rules.url_patterns and len(rules.url_patterns) > 0:
            pattern = compile(rules.url_patterns[0])
            result_filter = self._get_weather_page_classifier(weather_page_url_pattern=pattern)

        location_filter = self._get_location_filter(location_names=rules.keywords.include)
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

        self._logger.info(f"Crawl completed. Fetched {len(weather_pages)} results.")
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
                    parsed_result.value = parsed_result.value.replace("\r\n ", "").replace(" ", "")

            for daily_weather in parsed_results[1:]:
                self._logger.debug(f"Untransformed object: {daily_weather}")
                # result_dict = {key: daily_weather.value[key].value for key in daily_weather.value}
                weather_record = self._result_db_model.parse_obj(
                    daily_weather.value_to_dict())
                self._logger.debug(f"transformed model: {weather_record}")
                parsed_weather_history.append(weather_record)

        await self._result_db_model.insert_many(parsed_weather_history)
        self._logger.info("Crawl complete!")



class SpiderFactory(BaseServiceFactory):

    __spider_services__ = {
        "basic_page_scraping": HTMLSpiderService,
        "baidu_news_scraping": BaiduNewsSpider,
        "baidu_covid_report": BaiduCOVIDSpider,
        "weather_report": WeatherSpiderService,
        "air_quality": WeatherSpiderService
    }
    
    @classmethod
    def create(cls, spider_type: str, **kwargs):
        try:
            return cls.__spider_services__[spider_type.lower()](**kwargs)
        except Exception:
            return None



if __name__ == "__main__":
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    from ..models.request_models import (
        ScrapeRules, ParsingPipeline, ParseRule, KeywordRules, TimeRange
    )
    from ..core import Spider
    from yaml import load, dump
    from yaml import CLoader as Loader, CDumper as Dumper
    from os import getcwd


    def create_client(host: str, username: str,
                      password: str, port: int,
                      db_name: str) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin")


    def load_service_config(
        config_name: str,
        loader_func: Callable=load,
        loader_class: Any=Loader,
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
                                   html_model_class,
                                   test_urls,
                                   rules):
        db = db_client[db_name]
        result_model_class.db = db
        html_model_class.db = db

        async with (await client_session_class(headers=headers, cookies=cookies)) as client_session:
            spider_service = spider_service_class(request_client=client_session,
                                                  spider_class=spider_class,
                                                  parse_strategy_factory=parse_strategy_factory,
                                                  crawling_strategy_factory=crawling_strategy_factory,
                                                  result_db_model=result_model_class,
                                                  html_data_model=html_model_class)
            await spider_service.crawl(test_urls, rules)

    cookie_text = """BIDUPSID=C2730507E1C86942858719FD87A61E58;
    PSTM=1591763607; BAIDUID=0145D8794827C0813A767D21ADED26B4:FG=1;
    BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek;
    __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BD_UPN=123253; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5;
    H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP;
    """
    cookie_strings = cookie_text.replace("\n","").replace(" ","").split(";")
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
    use_db = 'spiderDB'
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name=use_db)
    urls = [
        # "https://voice.baidu.com/act/newpneumonia/newpneumonia",
        # "https://voice.baidu.com/act/newpneumonia/newpneumonia#tab4"
        # "http://www.baidu.com/s?tn=news&ie=utf-8",
        "http://www.tianqihoubao.com/lishi/"
    ]
    print(urls)

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
        spider_service_class=WeatherSpiderService,
        result_model_class=Weather,
        html_model_class=HTMLData,
        test_urls=urls,
        rules=load_service_config("weather_config")
    ))
