from datetime import date, datetime, timedelta, time
from typing import List, Any, Callable
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
                 request_client: AsyncBrowserRequestClient,
                 result_db_model: PHESCOVIDReport,
                 result_data_model: PHESCOVIDReportData,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = spider_service_logger):
        self._browser_request_client = request_client
        self._result_db_model = result_db_model
        self._result_data_model = result_data_model
        self._throttled_fetch = throttled_fetch
        self._logger = logger
        
    
    async def _load_report_data(self, url):
        try:
            await self._browser_request_client.launch_browser()
            page = await self._browser_request_client.browser.newPage()
            await page.goto(url)
            report_data = await page.evaluate(
                """
                () => {
                    return window.getAreaStat
                }
                """)
            await self._browser_request_client.close()
            covid_report = [DXYCOVIDReportData.parse_obj(report)
                            for report in report_data]
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
    
