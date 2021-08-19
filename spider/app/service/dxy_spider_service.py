from datetime import date, datetime, timedelta, time
from typing import List, Any, Callable
from .base_services import BaseSpiderService
from ..models.db_models import COVIDReport
from ..models.request_models import ScrapeRules
from ..models.data_models import DXYCOVIDReportData, COVIDReportData
from ..core import AsyncBrowserRequestClient
from ..utils import throttled
from lxml import etree
import pandas as pd
import numpy as np
import logging
import aiohttp
import asyncio
import json
import re
import traceback
from logging import Logger, getLogger
from dateutil import parser
from pymongo import UpdateOne, InsertOne, ReplaceOne

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(f"{__name__}.DXYSpider")
spider_service_logger.setLevel(logging.DEBUG)


class DXYCovidReportSpiderService(BaseSpiderService):

    def __init__(self,
                 request_client: AsyncBrowserRequestClient,
                 result_db_model: COVIDReport,
                 result_data_model: COVIDReportData,
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
        

    async def crawl(self, urls: List[str], rules: ScrapeRules, *args, **kwargs) -> Any:
        """ Crawl COVID Report from 丁香园
        """
        try:
            await self._browser_request_client.launch_browser()
            page = await self._browser_request_client.browser.newPage()
            page.setDefaultNavigationTimeout(10000000)
            await page.goto(urls[0], {'timeout': 10000*20})
            page_src = await page.content()
            parsed_page = etree.HTML(page_src)
            last_update_text = parsed_page.xpath(
                "//*[@id='root']/div/div[3]/div[5]/div[1]/div[2]/span/text()[1]")
            today = datetime.today().strftime("%Y-%m-%d")
            yesterday = datetime.combine((datetime.today() - timedelta(1)), time.min)
            
            last_update = yesterday.strftime("%Y-%m-%dT%H:%M:%S")
            if len(last_update_text):
                last_update = last_update_text[0][6:]
            
            recordDate = datetime.combine(parser.parse(
                last_update[:10]) - timedelta(1), time.min).strftime("%Y-%m-%dT%H:%M:%S")
            provincial_report_data = await page.evaluate(
                """
                () => {
                    return window.getAreaStat
                }
                """)
            await self._browser_request_client.close()
            
            covid_report = [DXYCOVIDReportData.parse_obj(report)
                            for report in provincial_report_data]
            national_increase_text = parsed_page.xpath(
                "//*[@id='root']/div/div[2]/div[2]/div[1]/div[1]/div[1]/div[1]/span//text()")
            national_increase = -1
            if len(national_increase_text) and national_increase_text[0].startswith("全国｜新增确诊"):
                national_increase_match = re.findall(
                    r"\d+", national_increase_text[0])
                national_increase = int(national_increase_match[0]) if len(national_increase_match) > 0 else -1
            
            report_tm1 = await self._result_db_model.get(
                {"recordDate": {
                    "$gte": (parser.parse(recordDate) - timedelta(1)).strftime("%Y-%m-%d"),
                    "$lt": parser.parse(recordDate).strftime("%Y-%m-%d")
                }})
            
            report_df_tm1 = pd.DataFrame([report.dict() for report in report_tm1])
            report_t = await self._result_db_model.get({
                'recordDate': {
                    "$gte": parser.parse(recordDate).strftime("%Y-%m-%d"),
                    '$lt': (parser.parse(recordDate) + timedelta(1)).strftime("%Y-%m-%d"),
                }})
            self._logger.info(report_df_tm1)
            self._logger.info(covid_report[0])
            self._logger.info(f"report_tm1 recordDate first: {report_df_tm1.recordDate.iloc[0]}")
            self._logger.info(
                f"report_tm1 recordDate last: {report_df_tm1.recordDate.iloc[-1]}")
            self._logger.info(f"report_tm1 size: {len(report_tm1)}")
            self._logger.info(
                f"report_t recordDate: {recordDate}")
            self._logger.info(f"report_t size: {len(report_t)}")
            
            should_update_report = (
                len(report_t) > 0 and
                len(covid_report) > 0)
            
            self._logger.info(f"fetched report size: {len(covid_report)}")
            self._logger.info(f"should_update_report: {should_update_report}")
            
            provincial_report_write_requests = []
            city_reports_write_requests = []
            imported_case_write_requests = []
            
            for report in covid_report:
                # provincial data
                if 'province' in report_df_tm1:
                    provincial_tm1 = report_df_tm1.query(
                        """
                        (province == @report.provinceName) and (city.isnull())
                        """, engine="python")
                    importedCase_tm1 = report_df_tm1.query(
                        """
                        (province == @report.provinceName) and (city == '境外输入')
                        """
                    )
                else:
                    provincial_tm1 = None
                    importedCase_tm1 = None
                    
                provincial_case_increase = (
                    report.confirmedCount - provincial_tm1.localNowReported.values[0]
                    if provincial_tm1 is not None and len(provincial_tm1.localNowReported) else -1)
                importedCases = [
                    city_report for city_report in report.cities if city_data.cityName == '境外输入']
                
                nowExistingImportedCases = importedCases[0].currentConfirmedCount if len(importedCases) > 0 else 0
                
                localNowExistedCases = report.currentConfirmedCount - nowExistingImportedCases
                
                self._logger.info(
                    f"importedCases: {importedCases}")
                self._logger.info(
                    f"nowExistingImportedCases: {nowExistingImportedCases}")
                self._logger.info(
                    f"recordDate: {recordDate}, lastUpdate: {last_update}")
                
                provincial_report = self._result_db_model(
                    province=report.provinceName,
                    city=None,
                    areaCode=report.locationId,
                    localNowReported=report.confirmedCount,         
                    localNowExisted=localNowExistedCases if not np.isnan(
                        localNowExistedCases) else report.currentConfirmedCount,
                    localIncreased=provincial_case_increase,
                    otherHasIncreased=1 if national_increase > provincial_case_increase else 0,
                    localNowCured=report.curedCount,
                    localNowCuredIncrease=(
                        report.curedCount - provincial_tm1.localNowCured.values[0]
                        if provincial_tm1 is not None and len(provincial_tm1.localNowCured) else -1),
                    localNowDeath=report.deadCount,
                    localDeathIncrease=(
                        report.deadCount - provincial_tm1.localNowDeath.values[0]
                        if provincial_tm1 is not None and len(provincial_tm1.localNowDeath) else -1),
                    suspectCount=report.suspectedCount,
                    suspectIncrease=(
                        report.suspectedCount - provincial_tm1.suspectCount.values[0]
                        if provincial_tm1 is not None and len(provincial_tm1.suspectCount) else -1
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
                    # self._logger.info(
                    #     f"save new provincial report: {provincial_report}")
                    await provincial_report.save()
                
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
                        self._result_db_model.bulk_write(
                            imported_case_write_requests)
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
    from ..db import create_client
    from ..models.data_models import RequestHeader
    
    async def test_spider():
        use_db = 'test'
        db_client = create_client(host='localhost',
                                username='admin',
                                password='root',
                                port=27017,
                                db_name=use_db)
        db = db_client[use_db]
        COVIDReport.db = db
        headers = RequestHeader(
            accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        )
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
                
        async with (await AsyncBrowserRequestClient(headers=headers, cookies=cookies)) as client_session:
            spider_service = DXYCovidReportSpiderService(
                browser_request_client=client_session, result_db_model=COVIDReport)
            await spider_service.load_historical_report('https://ncov.dxy.cn/ncovh5/view/pneumonia')
            await spider_service.crawl(['https://ncov.dxy.cn/ncovh5/view/pneumonia'], None)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider())



