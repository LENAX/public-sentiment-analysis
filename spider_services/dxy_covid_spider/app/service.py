from datetime import date, datetime, timedelta, time
from typing import List, Any, Callable
from spider_services.common.core.parser import ParserContextFactory

from spider_services.common.core.request_client import BaseRequestClient
from spider_services.common.core.spider import BaseSpider
from spider_services.common.models.request_models.request_models import ParsingPipeline
from ...common.service.base_services import BaseSpiderService
from ...common.models.db_models import PHESCOVIDReport
from ...common.models.request_models import ScrapeRules
from ...common.models.data_models import DXYCOVIDReportData, PHESCOVIDReportData, DangerArea
from ...common.core import AsyncBrowserRequestClient
from ...common.utils import throttled
from lxml import etree
import pandas as pd
import numpy as np
import logging
import aiohttp
import asyncio
import json
import re
import traceback
from logging import Logger
from dateutil import parser
from pymongo import UpdateOne, InsertOne, ReplaceOne

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(f"{__name__}.DXYSpider")
spider_service_logger.setLevel(logging.DEBUG)


class DXYCovidReportSpiderService(BaseSpiderService):

    def __init__(self,
                 request_client: BaseRequestClient,
                 result_db_model: PHESCOVIDReport,
                 result_data_model: PHESCOVIDReportData,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = spider_service_logger):
        self._browser_request_client = request_client
        self._result_db_model = result_db_model
        self._result_data_model = result_data_model
        self._spider_class = spider_class
        self._parser_factory = parse_strategy_factory
        self._throttled_fetch = throttled_fetch
        self._logger = logger
        
    
    async def _load_report_data(self, url: str, parse_step: ParsingPipeline):
        try:
            spider = self._spider_class(request_client=self._request_client, url_to_request=url)
            page = await spider.fetch()
            parser = self._parser_factory.create(parse_step.parser)
            parsed_result = parser.parse(page, parse_step.parse_rules)
            covid_report = [DXYCOVIDReportData.parse_obj(report.value_to_dict())
                            for report in parsed_result]
            return covid_report
        except Exception as e:
            self._logger.error(e)
            raise e
        
    async def _fetch_historical_report(self, url, province_name, areaCode):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                json_str = await response.text()
                return province_name, areaCode,  json.loads(json_str)
    
    async def load_historical_report(self, url, start_date=parser.parse("20200121"), end_date=datetime.now()):
        """ Load historical covid report into the database.
        """
        try:
            # if the db is empty, populate the database with historical covid report
            report_data = await self._load_report_data(url)
            provincial_covid_history_fetch_tasks = [
                self._fetch_historical_report(
                    report.statisticsData, report.provinceName, report.locationId)
                for report in report_data
            ]
            
            provincial_covid_history_list = await self._throttled_fetch(
                10, provincial_covid_history_fetch_tasks)
            provincial_historical_reports = []

            for report_tup in provincial_covid_history_list:
                province, areaCode, report_dict = report_tup
                reports = [DXYCOVIDReportData.parse_obj(report)
                          for report in report_dict['data']]
                if len(reports) == 0:
                    self._logger.warn("Failed to retrive historical data")
                    continue
                
                for report in reports:
                    report_date = parser.parse(str(report.dateId))
                    
                    if type(start_date) is str:
                        start_date = parser.parse(start_date)
                        
                    if type(end_date) is str:
                        end_date = parser.parse(end_date)
                    
                    if start_date <= report_date and report_date <= end_date:
                        provincial_report = self._result_db_model(
                            province=province,
                            city=None,
                            areaCode=areaCode,
                            localNowExisted=report.currentConfirmedCount,
                            localIncreased=report.confirmedIncr,
                            localNowReported=report.confirmedCount,
                            localNowCured=report.curedCount,
                            localNowCuredIncrease=report.curedIncr,
                            localNowDeath=report.deadCount,
                            localDeathIncrease=report.deadIncr,
                            otherHasIncreased=-1,
                            suspectCount=report.suspectedCount,
                            suspectIncrease=report.suspectedCountIncr,
                            dangerAreas=[DangerArea.parse_obj(area) for area in report.dangerAreas if report.dangerAreas is not None],
                            highDangerZoneCount=report.highDangerCount,
                            midDangerZoneCount=report.midDangerCount,
                            isImportedCase=False,
                            recordDate=report_date.strftime("%Y-%m-%dT00:00:00")
                        )
                        
                        provincial_historical_reports.append(provincial_report)

            self._logger.info(
                f"Fetched {len(provincial_historical_reports)} provincial reports!")
            if len(provincial_historical_reports) > 0:
                await self._result_db_model.insert_many(provincial_historical_reports)
                
            self._logger.info("Done!")
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            raise e
    
    
    def _get_national_increase(self, page) -> int:
        national_increase_text = page.xpath(
            "//*[@id='root']/div/div[2]/div[2]/div[1]/div[1]/div[1]/div[1]/span//text()")
        national_increase = -1
        if len(national_increase_text) and national_increase_text[0].startswith("全国｜新增确诊"):
            national_increase_match = re.findall(
                r"\d+", national_increase_text[0])
            national_increase = int(national_increase_match[0]) if len(
                national_increase_match) > 0 else -1
        return national_increase

    def _get_last_update_dt(self, page) -> str:
        last_update_text = page.xpath(
            "//*[@id='root']/div/div[3]/div[5]/div[1]/div[2]/span/text()[1]")
        yesterday = datetime.combine(
            (datetime.today() - timedelta(1)), time.min)

        last_update = yesterday.strftime("%Y-%m-%dT%H:%M:%S")
        if len(last_update_text):
            last_update = last_update_text[0][6:]
            
        return last_update
    
    def _get_record_date(self, last_update: str) -> str:
        recordDate = datetime.combine(parser.parse(
            last_update[:10]) - timedelta(1), time.min).strftime("%Y-%m-%dT%H:%M:%S")
        return recordDate
    
    async def _get_area_stats(self, page):
        provincial_report_data = await page.evaluate(
            """
            () => {
                return window.getAreaStat
            }
            """)
        covid_report = [DXYCOVIDReportData.parse_obj(report)
                        for report in provincial_report_data]
        
        return covid_report
    
    async def _fetch_covid_data(self, url: str):
        await self._browser_request_client.launch_browser()
        page = await self._browser_request_client.browser.newPage()
        page.setDefaultNavigationTimeout(10000000)
        await page.goto(url, {'timeout': 10000*20})
        page_src = await page.content()
        parsed_page = etree.HTML(page_src)
        
        national_increase = self._get_national_increase(parsed_page)
        last_update = self._get_last_update_dt(parsed_page)
        record_date = self._get_record_date(last_update)
        covid_report = await self._get_area_stats(page)

        await self._browser_request_client.close()
        
        return covid_report, last_update, record_date, national_increase
    
    async def _get_tm1_report(self, record_date):
        report_tm1 = await self._result_db_model.get(
            {"recordDate": {
                "$gte": (parser.parse(record_date) - timedelta(1)).strftime("%Y-%m-%d"),
                "$lt": parser.parse(record_date).strftime("%Y-%m-%d")
            }})

        report_df_tm1 = pd.DataFrame([report.dict() for report in report_tm1])
        return report_df_tm1
    
    def _get_provincial_stat(self, report_df, province_name):
        if 'province' not in report_df:
            return None
        
        provincial_stat = report_df.query(
            """
            (province == @province_name) and (city.isnull())
            """, engine="python")
        return provincial_stat
    
    def _get_city_stat(self, report_df, province_name, city_name):
        if 'province' not in report_df:
            return None

        city_stat = report_df.query(
            """
            (province == @province_name) and (city == @city_name)
            """
        )
        return city_stat
        
        
    def _get_city_report(self, report_today, city_name):
        city_reports = report_today.cities
        
        for city_report in city_reports:
            if city_report.cityName == city_name:
                return city_report
            
        return None
        
    def _get_provincial_local_cumulative_case(self, report_today, imported_case_today, local_report_tm1, imported_case_tm1):
        fields_validated = all([
            report_today is not None and hasattr(report_today, 'confirmedCount') and type(report_today.confirmedCount) is int,
            (imported_case_today is not None and hasattr(imported_case_today, 'confirmedCount') and
             type(imported_case_today.confirmedCount) is int),
            (local_report_tm1 is not None and hasattr(local_report_tm1, "localNowReported") and
             local_report_tm1.localNowReported is not None and len(local_report_tm1.localNowReported.values) > 0 and
             not np.isnan(local_report_tm1.localNowReported.values[0])),
            (imported_case_tm1 is not None and hasattr(imported_case_tm1, "foreignNowReported") and
             imported_case_tm1.foreignNowReported is not None and len(imported_case_tm1.foreignNowReported.values) > 0 and
             not np.isnan(imported_case_tm1.foreignNowReported.values[0])),
        ])
    
        if not fields_validated:
            return -1
        
        localReported = report_today.confirmedCount - imported_case_today.confirmedCount
        # localIncreased = localReported - local_report_tm1.localNowReported.values[0]
        
        return localReported

    async def crawl(self, urls: List[str], rules: ScrapeRules, *args, **kwargs) -> Any:
        """ Crawl COVID Report from 丁香园
        """
        try:
            if len(urls) == 0:
                self._logger.error(f"No url is provided.")
                return
            
            covid_report, last_update, recordDate, national_increase = await self._fetch_covid_data(urls[0])
            
            report_df_tm1 = await self._get_tm1_report(recordDate)
            report_t = await self._result_db_model.get({
                'recordDate': {
                    "$gte": parser.parse(recordDate).strftime("%Y-%m-%d"),
                    '$lt': (parser.parse(recordDate) + timedelta(1)).strftime("%Y-%m-%d"),
                }})
            
            should_update_report = (
                len(report_t) >  0 and
                len(covid_report) > 0)
            
            provincial_reports = []
            provincial_report_write_requests = []
            city_reports_write_requests = []
            imported_case_write_requests = []
            
            for report in covid_report:
                # get yesterday's report according to today's data
                provincial_report_tm1 = self._get_provincial_stat(report_df_tm1, report.provinceName)
                importedCase_tm1 = self._get_city_stat(report_df_tm1, report.provinceName, '境外输入')
                
                if importedCase_tm1 is None:
                    importedCase_tm1 = self._get_city_stat(report_df_tm1, report.provinceName, '境外输入人员')
                
                imported_case_today = self._get_city_report(report, '境外输入')
                if imported_case_today is None:
                    importedCase_tm1 = self._get_city_stat(
                        report_df_tm1, report.provinceName, '境外输入人员')
                
                if any([provincial_report_tm1 is None, importedCase_tm1 is None, imported_case_today is None]):
                    self._logger.error(f'Cannot find reports of {report.provinceName} from yesterday!')
                    continue
                
                provincial_local_cases = self._get_provincial_local_cumulative_case(
                    report, imported_case_today, provincial_report_tm1, importedCase_tm1)
                localIncreased = provincial_local_cases - provincial_report_tm1.localNowReported.values[0]
                
                nowExistingImportedCases = imported_case_today.currentConfirmedCount
                localNowExistedCases = report.currentConfirmedCount - nowExistingImportedCases
                
                provincial_report = self._result_db_model(
                    province=report.provinceName,
                    city=None,
                    areaCode=report.locationId,
                    localNowReported=provincial_local_cases,
                    localNowExisted=localNowExistedCases if not np.isnan(
                        localNowExistedCases) else report.currentConfirmedCount,
                    localIncreased=localIncreased,
                    otherHasIncreased=1 if national_increase > localIncreased else 0,
                    localNowCured=report.curedCount,
                    localNowCuredIncrease=(
                        report.curedCount - imported_case_today.curedCount - provincial_report_tm1.localNowCured.values[0]
                        if provincial_report_tm1 is not None and len(provincial_report_tm1.localNowCured) else -1),
                    localNowDeath=report.deadCount,
                    localDeathIncrease=(
                        report.deadCount - imported_case_today.deadCount - provincial_report_tm1.localNowDeath.values[0]
                        if provincial_report_tm1 is not None and len(provincial_report_tm1.localNowDeath) else -1),
                    suspectCount=report.suspectedCount,
                    suspectIncrease=(
                        report.suspectedCount - imported_case_today.suspectCount - provincial_report_tm1.suspectCount.values[0]
                        if provincial_report_tm1 is not None and len(provincial_report_tm1.suspectCount) else -1
                    ),
                    highDangerZoneCount=report.highDangerCount,
                    midDangerZoneCount=report.midDangerCount,
                    isImportedCase=False,
                    recordDate=recordDate,
                    lastUpdate=last_update
                )
                
                if should_update_report:
                    updated_provincial_report = self._result_data_model.from_db_model(provincial_report)
                    self._logger.info(
                        f"update provincial report: {updated_provincial_report.province}")
                    provincial_report_write_requests.append(
                        UpdateOne({
                            "province": report.provinceName,
                            "areaCode": str(report.locationId),
                            'recordDate': {
                                "$gte": parser.parse(recordDate).strftime("%Y-%m-%d"),
                                '$lte': (parser.parse(recordDate) + timedelta(1)).strftime("%Y-%m-%d"),
                            }}, {'$set': updated_provincial_report.dict()}, upsert=True))
                else:
                    provincial_reports.append(provincial_report)
                    
                # city data
                city_reports = []
                for city_data in report.cities:
                    if 'province' in report_df_tm1.columns:
                        city_tm1_report = report_df_tm1.query(
                            """
                            (province == @report.provinceName) and (city == @city_data.cityName)
                            """)
                    else:
                        city_tm1_report = None
                    
                    if city_data.cityName == '境外输入':
                        imported_case = self._result_db_model(
                            province=report.provinceName,
                            city=city_data.cityName,
                            areaCode=city_data.locationId,
                            importedNowExisted=city_data.currentConfirmedCount,
                            foreignEnterIncrease=(
                                city_data.confirmedCount - city_tm1_report.foreignNowReported.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.importedNowExisted) else -1
                            ),
                            foreignNowReported=city_data.confirmedCount,
                            importedCuredCases=city_data.curedCount,
                            importedcuredCasesIncrease=(
                                city_data.curedCount - city_tm1_report.importedCuredCases.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.importedCuredCases) else -1
                            ),
                            foreignNowDeath=city_data.deadCount,
                            foreignNowDeathIncrease=(
                                city_data.deadCount - city_tm1_report.foreignNowDeath.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.foreignNowDeath) else -1
                            ),
                            suspectCount=city_data.suspectedCount,
                            suspectIncrease=(
                                city_data.suspectedCount - city_tm1_report.suspectCount.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.suspectCount) else -1
                            ),
                            otherHasIncreased=-1,
                            highDangerZoneCount=city_data.highDangerCount,
                            midDangerZoneCount=city_data.midDangerCount,
                            isImportedCase=True,
                            recordDate=recordDate,
                            lastUpdate=last_update
                        )
                        if should_update_report:
                            updated_imported_case = self._result_data_model.from_db_model(imported_case)
                            self._logger.info(
                                f"update imported case report: {updated_imported_case.province}")
                            imported_case_write_requests.append(UpdateOne({
                                "province": report.provinceName,
                                "city": city_data.cityName,
                                "isImportedCase": True,
                                'recordDate': {
                                    "$gte": parser.parse(recordDate).strftime("%Y-%m-%d"),
                                    '$lte': (parser.parse(recordDate) + timedelta(1)).strftime("%Y-%m-%d"),
                                }}, {'$set': updated_imported_case.dict()}, upsert=True))
                        else:
                            city_reports.append(imported_case)
                    else:
                        city_report = self._result_db_model(
                            province=report.provinceName,
                            city=city_data.cityName,
                            areaCode=city_data.locationId,
                            localNowExisted=city_data.currentConfirmedCount,
                            localIncreased=(
                                city_data.confirmedCount - city_tm1_report.localNowReported.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.localNowReported) else -1
                            ),
                            localNowReported=city_data.confirmedCount,
                            localNowReportedIncrease=(
                                city_data.confirmedCount - city_tm1_report.localNowReported.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.localNowReported) else -1
                            ),
                            localNowCured=city_data.curedCount,
                            localNowCuredIncrease=(
                                city_data.curedCount - city_tm1_report.localNowCured.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.localNowCured) else -1
                            ),
                            localNowDeath=city_data.deadCount,
                            localDeathIncrease=(
                                city_data.deadCount - city_tm1_report.localNowDeath.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.localNowDeath) else -1
                            ),
                            suspectCount=city_data.suspectedCount,
                            suspectIncrease=(
                                city_data.suspectedCount - city_tm1_report.suspectCount.values[0]
                                if city_tm1_report is not None and len(city_tm1_report.suspectCount) else -1
                            ),
                            otherHasIncreased=-1,
                            highDangerZoneCount=city_data.highDangerCount,
                            midDangerZoneCount=city_data.midDangerCount,
                            isImportedCase=False,
                            recordDate=recordDate,
                            lastUpdate=last_update
                        )
                    
                        if should_update_report:
                            updated_city_data = self._result_data_model.from_db_model(city_report)
                            self._logger.info(
                                f"updated city_report: {updated_city_data.city}")
                            city_reports_write_requests.append(
                                UpdateOne({
                                    "areaCode": str(city_data.locationId),
                                    'recordDate': {
                                        "$gte": parser.parse(recordDate).strftime("%Y-%m-%d"),
                                        '$lte': (parser.parse(recordDate) + timedelta(1)).strftime("%Y-%m-%d"),
                                    }}, {'$set': updated_city_data.dict()}, upsert=True))
                        else:
                            city_reports.append(city_report)
                
                if len(city_reports) > 0:
                    await self._result_db_model.insert_many(city_reports)
                    
                await self._result_db_model.insert_many(provincial_reports)
            
            if should_update_report:
                self._logger.info("Start executing bulk update operations")
                self._logger.info(
                    f"updating existing entries")
                
                try:
                    self._logger.info(
                        f"provincial_report_write_requests: {len(provincial_report_write_requests)}")
                    self._logger.info(
                        f"city_reports_write_requests: {len(city_reports_write_requests)}")
                    self._logger.info(
                        f"imported_case_write_requests: {len(imported_case_write_requests)}")
                    await asyncio.gather(*[
                        self._result_db_model.bulk_write(provincial_report_write_requests),
                        self._result_db_model.bulk_write(city_reports_write_requests),
                        self._result_db_model.bulk_write(imported_case_write_requests)
                    ])
                    
                except Exception as e:
                    traceback.print_exc()
                    self._logger.error(e)
                    raise e
            
            self._logger.info("Done!")
        except Exception as e:
            self._logger.error(e)
            raise e
    




if __name__ == "__main__":
    import asyncio
    from os import getcwd
    from typing import Any

    from devtools import debug
    from motor.motor_asyncio import AsyncIOMotorClient
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
    from yaml import dump, load

    from ...common.core import CrawlerContextFactory, RequestClient, Spider
    from ...common.models.data_models import RequestHeader
    from ...common.models.request_models import (KeywordRules, ParseRule,
                                                 ParsingPipeline, ScrapeRules,
                                                 TimeRange)


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
        config_path: str = f"{getcwd()}/spider_services/service_configs"
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
            
    def make_cookies(cookie_text):
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
        return cookies

    async def test_spider_services(db_client,
                                   db_name,
                                   headers,
                                   cookies,
                                   client_session_class,
                                   spider_class,
                                   parse_strategy_factory,
                                   crawling_strategy_factory,
                                   spider_service_class,
                                   data_model,
                                   result_model_class,
                                   test_urls,
                                   rules):
        db = db_client[db_name]
        result_model_class.db = db

        async with (await client_session_class(headers=headers, cookies=cookies)) as client_session:
            article_classification_service = ArticleClassificationService(
                'http://localhost:9000/article-category', client_session, ArticleCategory)
            article_popularity_service = ArticlePopularityService(
                'http://localhost:9000/article-popularity', client_session, ArticlePopularity
            )
            article_summary_service = ArticleSummaryService(
                'http://localhost:9000/content-abstract', client_session, ArticleSummary
            )

            spider_service = spider_service_class(request_client=client_session,
                                                  spider_class=spider_class,
                                                  parse_strategy_factory=parse_strategy_factory,
                                                  crawling_strategy_factory=crawling_strategy_factory,
                                                  data_model=data_model,
                                                  db_model=result_model_class,
                                                  article_classification_service=article_classification_service,
                                                  article_popularity_service=article_popularity_service,
                                                  article_summary_service=article_summary_service)
            await spider_service.crawl(test_urls, rules)

    cookie_text = """
    BIDUPSID=C2730507E1C86942858719FD87A61E58; PSTM=1591763607; BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek; __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5; H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP; BDUSS_BFESS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek; H_WISE_SIDS=110085_127969_128698_164869_170704_171235_173017_173293_174035_174449_174661_174665_175038_175407_175609_175665_175756_176157_176348_176398_176418_176589_176678_176766_176960_176995_177085_177094_177168_177283_177317_177393_177401_177412_177520_177522_177565_177632_177727_177735_177787_178076_178152_178205_178327_178384_178639; BAIDUID=F77119553DDCA3E3D26F14FA5EBF834C:FG=1; BAIDUID_BFESS=F77119553DDCA3E3D26F14FA5EBF834C:FG=1; delPer=0; PSINO=7; BAIDU_WISE_UID=wapp_1632905041500_81;  BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; BA_HECTOR=208500852hak2l047b1gldcon0q; H_PS_PSSID=; MBDFEEDSG=df5a2f94d6addda8f42862cac42480f2_1633073378; ab_sr=1.0.1_NDQ3Yjc4OTliYTExNWM4YmVjZDY4YTQzZmIyZWJhM2VjZDg2MmU2OGVlMzMxZTUyMmU0ZDE1NGZiMjI0OWU2OWI5NGQwZGQ5ODIzMTZjOTA1MzI5NjdhZTM5NDNmMjIwZjhjZWRlNDQyYjVjNTUyZDc5MWI2MGU5MGM2OTAyNjcyMDRkMTQ1ODRlOTFmNjZiMTE5NDIyN2JjYWYzZDFkMw==
    """
    cookies = make_cookies(cookie_text)

    headers = RequestHeader(
        accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",)
    use_db = 'test'
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name=use_db)
    urls = [
        "http://www.baidu.com/s?tn=news&ie=utf-8"
    ]
    print(urls)
    config = load_service_config("baidu_news")
    debug(config)
    
    
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
        spider_service_class=BaiduNewsSpiderService,
        data_model=News,
        result_model_class=NewsDBModel,
        test_urls=urls,
        rules=config
    ))

