import re
import json
import asyncio
from functools import partial
from datetime import datetime
from pymongo import InsertOne, DeleteMany, ReplaceOne, UpdateOne
from typing import List, Callable, Union
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor
from ...common.service.base_services import BaseSpiderService
from ...common.models.data_models import (
    HourlyForecast, TodayForecast, DailyForecast,
    WeeklyWeatherForecast, WeatherNow, Location, WeatherAlert, WeatherReport)

from ...common.models.request_models import ScrapeRules, ParseRule
from ...common.models.db_models import WeatherReportDBModel
from ...common.core import (
    BaseSpider, ParserContextFactory, AsyncBrowserRequestClient, CrawlerContextFactory)
from ...common.utils import throttled
import traceback
import logging
from logging import Logger, getLogger
from dateutil import parser

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)


class WeatherForecastSpiderService(BaseSpiderService):
    """ A spider for crawling weather forecasts
    
    """

    def __init__(self,
                 request_client: AsyncBrowserRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 crawling_strategy_factory: CrawlerContextFactory,
                 result_db_model: WeatherReportDBModel,
                 result_data_model: WeatherReport,
                 crawl_method: str = 'bfs_crawler',
                 link_finder: str = 'link_parser',
                 coroutine_runner: Callable = asyncio.gather,
                 event_loop_getter: Callable = asyncio.get_event_loop,
                 process_pool_executor=ProcessPoolExecutor,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = getLogger(f"{__name__}.WeatherForecastSpiderService"),
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
        self._result_data_model = result_data_model
        self._xhr_response = {}
        self._coroutine_runner = coroutine_runner
        self._event_loop_getter = event_loop_getter
        self._process_pool_executor = process_pool_executor
        self._throttled_fetch = throttled_fetch
        self._logger = logger
        self._page_request_results = []
        self._weather = [
            '晴', '多云', '阴', '阵雨', '雷阵雨','雷雪','雨夹雪','小雨',
            '中雨', '大雨', '暴雨', '大暴雨', '特大暴雨', '阵雪', '小雪', 
            '中雪', '大雪', '暴雪', '雾', '大雨', '浮尘', '中雨', '暴雨',
            '大暴雨', '特大暴雨', '中雪', '大雪', '暴雪', '雾', '雾霾', '日食',
            '浮尘', '日食/雾', '日食/暴雨', '日食/中雪', '日食/浮尘', '日食/大暴雨'
        ]
    
    def _make_xhr_interceptor(self):
        """ Intercept XHR requests and store the response data
        """
        async def intercept_xhr(response, response_store: dict, logger: Any):
            # In this example, we care only about responses returning JSONs
            if "application/json" in response.headers.get("content-type", ""):
                try:
                    # Print some info about the responses
                    response_data = await response.json()
                    response_store[response.url] = {
                        "url": response.url,
                        "status": response.status,
                        "headers": response.headers,
                        "method": response.request.method,
                        "data": response_data
                    }
                except json.decoder.JSONDecodeError:
                    # NOTE: Use await response.text() if you want to get raw response text
                    logger.error("Failed to decode JSON from", await response.text())
        
        self._xhr_response = {}
        return partial(intercept_xhr, response_store=self._xhr_response, logger=self._logger)


    async def _request_report_page(self, url, req_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                self._logger.info(f"completed requesting {url} of {req_id}")
                self._page_request_results.append((url, html))
                
                
    async def _request_report_api(self, url, req_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                json_data = await response.json()
                self._logger.info(f"completed requesting {url} of {req_id}")
                self.resp_data.append(json_data)           
    
    
    async def _visit_homepage(self, url) -> bool:
        await self._request_client.launch_browser()
        page = await self._request_client.browser.newPage()
        page.on('response', self._make_xhr_interceptor())
        await page.goto(url, {'timeout': 1000000*20})

        # wait until xhr responses are intercepted
        attempt = 0
        while attempt < 100 and len(self._xhr_response) < 2:
            # the weather website will make two api calls
            await asyncio.sleep(0.1)
            attempt += 1

        if len(self._xhr_response) < 2:
            self._logger.error(
                f"Expected to receive at least 2 xhr response. Received {len(self._xhr_response)} instead.")
            return False
        
        return True
    
    def _get_national_weather_report(self) -> Union[dict, None]:
        # now there should be at least 2 xhr results
        national_weather_api_url = [key for key in self._xhr_response.keys()
                                    if re.search(r'api/map/weather', key)]
        
        if len(national_weather_api_url) != 1:
            self._logger.error(
                f"Expected to match exactly 1 xhr response, but matched {len(national_weather_api_url)} instead."
                f"Matched: {national_weather_api_url}"
                f"XHR responses: {self._xhr_response}")
            return None
        
        national_weather_report_resp = self._xhr_response[national_weather_api_url[0]]

        if not (type(national_weather_report_resp) is dict and
                'data' in national_weather_report_resp):
            self._logger.error(
                f"Expected response having fields data, but it only has {list(national_weather_report_resp.keys())}.")
            return None

        weather_report_data = national_weather_report_resp['data']
        if not (type(weather_report_data is dict and
                'data' in weather_report_data and
                'msg' in weather_report_data and
                'status' in weather_report_data)):
            self._logger.error(
                f"Expected response data having fields (data, msg, status), but it only has {list(weather_report_data.keys())}."
                f"weather_report_data: {weather_report_data}")
            return None
        
        if (not self._is_weather_report_valid(weather_report_data)):
            self._logger.error("Field missing in weather_report_data." 
                               "Expected to have field data, city."
                               f"Got {weather_report_data} instead.")
            return None
        
        return weather_report_data['data']['city']
    
    def _is_weather_report_valid(self, weather_report_data):
        return (weather_report_data is not None and
                weather_report_data['code'] == 0 and
                weather_report_data['msg'] == 'success' and
                weather_report_data['data'] is not None and
                'city' in weather_report_data['data'] and
                len(weather_report_data['data']['city']) > 0)
        
    def _get_today_forecasts(self, weather_data):
        city_today_forecast_tuple = namedtuple(
            'city_today_forecast_tuple',
            ['locationId', 'city', 'country', 'administrativeDivision',
                "xAxis", "yAxis", "highestTemperature", 'morningWeather', 'weatherIconId',
                'morningWindDirection', 'morningWindScale', 'lowestTemperature', 'eveningWeather', 'hasWeatherChanged',
                'eveningWindDirection', 'eveningWindScale', 'unknown', 'areaCode'])
        
        self.city_weather_reports = {}
        for city_weather_data in weather_data:
            today_forecast_tup = city_today_forecast_tuple._make(city_weather_data)
            today_forecast = TodayForecast(**today_forecast_tup._asdict())
            location = Location(**today_forecast_tup._asdict())
            last_update = weather_data['lastUpdate'] if 'lastUpdate' in weather_data else datetime.now().strftime('%Y/%m/%d %H:%M:%S')

            self.city_weather_reports[today_forecast_tup.locationId] = WeatherReport(
                todayForecast=today_forecast,
                location=location,
                last_update=parser.parse(last_update),
                create_dt=datetime.now()
            )
    
    def _is_valid_response_data(self, data):
        return (type(data) is dict and
                'data' in data and
                'code' in data and data['code'] == 0 and
                'msg' in data and data['msg'] == 'success')
        
    def _contains_fields(self, data: dict, fields: List[str]) -> bool:
        return all([(field in data) for field in fields])
    
    def _get_city_location(self, weather_report: dict) -> dict:
        city_location = weather_report['location']

        if not (self._contains_fields(city_location, ['id', 'path']) and
                type(city_location['id']) is str and
                type(city_location['path']) is str):
            self._logger.error("id and path not available!")
            return {}

        return city_location
    
    def _fill_location_data(self, city_location: dict) -> bool:
        if 'id' not in city_location:
            return False
        
        location_id = city_location['id']
        country, province, city = city_location['path'].split(',')

        if self.city_weather_reports[location_id].location is not None:
            self.city_weather_reports[location_id].location.province = province.strip()
            return True
        else:
            self.city_weather_reports[location_id].location = Location(
                locationId=location_id,
                city=city,
                country=country,
                province=province
            )
            self._logger.error(
                "Failed to fill location data in stage one.")
            return False
        
    def _fill_weather_now(self, weather_report, location_id):
        if self.city_weather_reports[location_id].weatherNow is None:
            self.city_weather_reports[location_id].weatherNow = []
            
        self.city_weather_reports[location_id].weatherNow.append(
            WeatherNow(**weather_report['now']))
        if self.city_weather_reports[location_id].weatherNow is None:
            self._logger.error(
                "Failed to fill weather now data in stage one.")

    def _fill_weather_alert(self, weather_report, location_id):
        if len(weather_report['alarm']) > 0:
            self.city_weather_reports[location_id].weatherAlerts = [
                WeatherAlert(**alert) for alert in weather_report['alarm']]
        else:
            self.city_weather_reports[location_id].weatherAlerts = []


    async def crawl(self, urls: List[str], rules: ScrapeRules):
        data_today = await self._result_db_model.get({'create_dt': {'$gte': datetime.today().strftime("%Y-%m-%d")}})
        if data_today is not None and len(data_today) > 0:
            await self._update_existing_data(rules, data_today)
        else:
            await self._crawl_new_data(urls, rules)


    async def _update_existing_data(self, rules: ScrapeRules, existing_data: List[WeatherReportDBModel]):
        """ Update existing weather report by adding new current weather report data
        """
        try:
            weather_reports = {
                report.location.locationId: report
                for report in existing_data
                if report.location is not None and report.location.locationId is not None
            }
            weather_report_urls = [
                f"https://weather.cma.cn/api/now/{locationId}"
                for locationId in weather_reports]

            self.resp_data: List[dict] = []
            await self._throttled_fetch(
                rules.max_concurrency,
                [self._request_report_api(url, i)
                 for i, url in enumerate(weather_report_urls)])

            update_operations = []
            for data in self.resp_data:
                if not self._is_valid_response_data(data):
                    continue

                weather_report = data['data']
                if not (type(weather_report) is dict and
                        self._contains_fields(weather_report, [
                            'location', 'now', 'alarm', 'lastUpdate'])):
                    continue
                
                city_location = self._get_city_location(weather_report)
                if not 'id' in city_location:
                    continue
                
                location_id = city_location['id']
                weather_now = WeatherNow(**{**weather_report['now'],
                                            **{'lastUpdate': weather_report['lastUpdate']}})
                
                if type(weather_reports[location_id].weatherNow) is list:
                    weather_reports[location_id].weatherNow.append(weather_now)
                else:
                    self._logger.warn("Original weather now list is empty!")
                    weather_reports[location_id].weatherNow = [weather_now]
                
                update_operations.append(UpdateOne(
                    {"weather_id": weather_reports[location_id].weather_id},
                    {"$set": {'weatherNow': weather_reports[location_id].weatherNow}}
                ))
                
            await self._result_db_model.bulk_write(update_operations)
            
        except Exception as e:
            self._logger.error(f"{e}")

    async def _crawl_new_data(self, urls: List[str], rules: ScrapeRules) -> None:
        # open a new browser instance
        try:
            if len(urls) < 0:
                self._logger.warn("No valid URL is provided.")
                return
            
            fetch_successful = await self._visit_homepage(urls[0])
            
            if not fetch_successful:
                return
            
            weather_data = self._get_national_weather_report()
            
            if weather_data is None:
                return
            
            self._get_today_forecasts(weather_data)
                
            weather_report_urls = [
                f"https://weather.cma.cn/api/now/{locationId}"
                for locationId in self.city_weather_reports]
         
            self.resp_data: List[dict] = []
            await self._throttled_fetch(
                rules.max_concurrency,
                [self._request_report_api(url, i)
                 for i, url in enumerate(weather_report_urls)])
            
            # update city's current weather
            for data in self.resp_data:
                if not self._is_valid_response_data(data):
                    continue
                
                weather_report = data['data']
                if not (type(weather_report) is dict and
                        self._contains_fields(weather_report, [
                            'location', 'now', 'alarm', 'lastUpdate'])):
                    continue
                
                city_location = self._get_city_location(weather_report)
                self._fill_location_data(city_location)
            
                if not 'id' in city_location:
                    continue
                
                location_id = city_location['id']
                self._fill_weather_now(weather_report, location_id)
                self._fill_weather_alert(weather_report, location_id)

                
                if (self.city_weather_reports[location_id].weatherNow is None or 
                    self.city_weather_reports[location_id].weatherAlerts is None):
                    self._logger.error(
                        f"Failed to fill weather data for location id: {location_id}.")
                    self._logger.info(
                        f"{self.city_weather_reports[location_id]}")
                    
            update_time_parser = self._parse_strategy_factory.create(
                rules.parsing_pipeline[0].parser)
            daily_forecast_parser = self._parse_strategy_factory.create(
                rules.parsing_pipeline[1].parser)
            hourly_forecast_parser = self._parse_strategy_factory.create(
                rules.parsing_pipeline[2].parser)
            
            weather_forecast_urls = [f"https://weather.cma.cn/web/weather/{locationId}"
                                        for locationId in self.city_weather_reports]
            
            await self._throttled_fetch(
                rules.max_concurrency,
                [self._request_report_page(url, i) for i, url in enumerate(weather_forecast_urls)])
            
            for i, result in enumerate(self._page_request_results):
                self._logger.info(f"Parsing {i}/{len(self._page_request_results)}")
                url, html = result
                locationId = url.split('/')[-1].split('.')[0]
                city_report = self.city_weather_reports[locationId]
                last_update_parse_results = update_time_parser.parse(
                    html, rules.parsing_pipeline[0].parse_rules)
                daily_forecast_parse_results = daily_forecast_parser.parse(
                    html, rules.parsing_pipeline[1].parse_rules)
                hourly_forecast_parse_results = hourly_forecast_parser.parse(
                    html, rules.parsing_pipeline[2].parse_rules)
                
                daily_forecasts = []
                for i, daily_forecast_results in enumerate(daily_forecast_parse_results):
                    result = daily_forecast_results.value
                    today_forecast = TodayForecast(
                        **{key: result[key].value for key in result})
                    
                    # there are 8 hourly forecasts everyday
                    hourly_forecast_results = [
                        HourlyForecast(
                            **{key: hourly_forecast_result.value[key].value for key in hourly_forecast_result.value})
                        for hourly_forecast_result in hourly_forecast_parse_results[i*8: i*8+7]
                    ]
                    for hourly_forecast in hourly_forecast_results:
                        if type(hourly_forecast.weather) is str and hourly_forecast.weather.isdigit():
                            hourly_forecast.weather = self._weather[int(hourly_forecast.weather)]

                    daily_forecast = DailyForecast(
                        day=result['day'].value,
                        date=result['date'].value,
                        today=today_forecast,
                        hourlyForecast=hourly_forecast_results
                    )
                    daily_forecasts.append(daily_forecast)
                
                self._logger.info(
                    f"Constructed daily_forecast")
                report_update_time = (last_update_parse_results[0].value['lastUpdate'].value
                                        if len(last_update_parse_results) > 0 else datetime.now())

                city_report.weeklyForecast = WeeklyWeatherForecast(
                    data=daily_forecasts,
                    last_update=report_update_time
                )
                self._logger.info(
                    f"Constructed weeklyForecast")
                
            await self._result_db_model.insert_many(
                [self._result_db_model.parse_obj(report)
                    for report in self.city_weather_reports.values()])
            self._logger.info('Done!')
                
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            raise e


if __name__ == "__main__":
    import asyncio
    from typing import Any
    from motor.motor_asyncio import AsyncIOMotorClient
    from ...common.models.request_models import (
        ScrapeRules, ParsingPipeline, ParseRule, KeywordRules, TimeRange,
    )
    from ...common.models.data_models import RequestHeader
    from ...common.models.db_models import WeatherReportDBModel
    from ...common.core import Spider
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
    print(urls)
    # config = load_service_config("aqi_config")
    # debug(config)
    
    config = ScrapeRules(
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

    loop = asyncio.get_event_loop()
    # cProfile.run("""loop.run_until_complete(test_spider_services(
    #     db_client=db_client,
    #     db_name=use_db,
    #     headers=headers.dict(),
    #     cookies=cookies,
    #     client_session_class=AsyncBrowserRequestClient,
    #     spider_class=Spider,
    #     parse_strategy_factory=ParserContextFactory,
    #     crawling_strategy_factory=CrawlerContextFactory,
    #     spider_service_class=WeatherForecastSpiderService,
    #     result_model_class=WeatherReportDBModel,
    #     result_data_model=WeatherReport,
    #     test_urls=urls,
    #     rules=config
    # ))""")
    loop.run_until_complete(test_spider_services(
        db_client=db_client,
        db_name=use_db,
        headers=headers.dict(),
        cookies=cookies,
        client_session_class=AsyncBrowserRequestClient,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        spider_service_class=WeatherForecastSpiderService,
        result_model_class=WeatherReportDBModel,
        result_data_model=WeatherReport,
        test_urls=urls,
        rules=config
    ))
