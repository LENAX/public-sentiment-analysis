from fastapi import APIRouter, Depends, HTTPException
from ..models.response_models import Response
from ..models.data_models import COVIDReportData
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..containers import Application
from ..service import COVIDReportService
from datetime import datetime, time, timedelta

import logging

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
covid_report_logger = logging.getLogger(__name__)
covid_report_logger.setLevel(logging.DEBUG)


covid_report_controller = APIRouter()


@covid_report_controller.get("/covid-report", tags=["results"], response_model=Response[List[COVIDReportData]])
@inject
async def get_report(areaCode: str,
                     startDate: Optional[str] = (datetime.combine((datetime.today() - timedelta(1)), time.min).isoformat()),
                     endDate: Optional[str] = (datetime.combine((datetime.today()), time.max).isoformat()),
                     returnAllCities: Optional[int] = 1,
                     importedCase: Optional[int] = 0,
                     covid_report_service: COVIDReportService = Depends(Provide[Application.services.covid_report_service])):
    
    covid_report_logger.info(
        f"Received request, areaCode: {areaCode}, startDate: {startDate}, endDate: {endDate}"
        f"returnAllCities: {returnAllCities}, importedCase: {importedCase}"
    )
    
    if not importedCase and areaCode != '0':
        # 查询本土病例
        covid_report_logger.info("Query for domestic cases")
        covid_reports = await covid_report_service.get_many({
            'areaCode': areaCode,
            'recordDate': {'$gte': startDate, '$lte': endDate},
        })
        
        if areaCode.endswith('0000') and returnAllCities:
            # 如果是查询了省级的数据，当附带市级数据选项为真时，查询该省下的所有市的数据
            if len(covid_reports) > 0:
                provincial_report = covid_reports[0]
                city_reports = await covid_report_service.get_many({
                    'province': provincial_report.province,
                    'city': {"$ne" : None},
                    'recordDate': {'$gte': startDate, '$lte': endDate},
                    'isImportedCase': False
                })
                covid_reports.extend(city_reports)
  
        return Response[List[COVIDReportData]](
                    data=covid_reports,
                    status="ok",
                    statusCode=200,
                    message="success")
    else:
        covid_reports = await covid_report_service.get_many({
            'areaCode': areaCode,
            'recordDate': {'$gte': startDate, '$lte': endDate},
        })
        
        if len(covid_reports) == 0:
            return Response[List[COVIDReportData]](
                    data=[],
                    status="ok",
                    statusCode=200,
                    message="success")
        
        if areaCode != '0':
            imported_cases = await covid_report_service.get_many({
                'province': covid_reports[0].province,
                'recordDate': {'$gte': startDate, '$lte': endDate},
                'isImportedCase': True
            })
            return Response[List[COVIDReportData]](
                    data=imported_cases,
                    status="ok",
                    statusCode=200,
                    message="success")
        else:
            # 直接查找全国的境外输入病例
            return Response[List[COVIDReportData]](
                data=covid_reports,
                status="ok",
                statusCode=200,
                message="success")
        
