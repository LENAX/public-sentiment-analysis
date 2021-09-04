import re
import asyncio
from datetime import datetime, timedelta
from typing import List, Callable
from concurrent.futures import ProcessPoolExecutor
from ...common.service.base_services import BaseSpiderService
from ...common.models.request_models import ScrapeRules
from ...common.models.db_models import News
from ...common.core import BaseSpider, ParserContextFactory, BaseRequestClient
from ...common.utils import throttled
import logging
from logging import Logger, getLogger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)


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
            spiders.extend(self._spider_class.create_from_urls(
                search_urls, self._request_client))

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
            content_urls = [
                result.value['href'].value for result in parsed_search_result]
            content_spiders = self._spider_class.create_from_urls(
                content_urls, self._request_client)
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

            parsed_contents = content_parser.parse(
                content_page, rules.parsing_pipeline[1].parse_rules)
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


