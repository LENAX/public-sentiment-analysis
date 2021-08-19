from typing import List, Any, Coroutine
from .base_services import BaseAsyncCRUDService
from ..models.db_models import COVIDReport
from ..models.data_models import COVIDReportData
from ..models.request_models import QueryArgs
import logging
from logging import Logger, getLogger

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y/%m/%d %H:%M:%S %p"
logging.basicConfig(level=logging.DEBUG,
                    format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class COVIDReportService(BaseAsyncCRUDService):
    """ Provides COVIDReport Data Access
    """

    def __init__(self,
                 covid_report_db_model: COVIDReport = COVIDReport,
                 covid_report_data_model: COVIDReportData = COVIDReportData,
                 logger: Logger = getLogger(f"{__name__}.COVIDReportService")):
        self._covid_report_db_model = covid_report_db_model
        self._covid_report_data_model = covid_report_data_model
        self._logger = logger

    # type: ignore[override]
    async def add_one(self, data: COVIDReportData) -> COVIDReportData:
        """ Add a new covid_report record

        Args:
            data (COVIDReportData): covid_report data model

        Returns:
            COVIDReportData: the newly added covid_report record
        """
        try:
            new_covid_report_record = self._covid_report_db_model.parse_obj(data)
            await new_covid_report_record.save()
            return self._covid_report_data_model.from_db_model(new_covid_report_record)
        except Exception as e:
            self._logger.error(
                "Fail to create a new covid_report record", exc_info=True)
            raise e


    async def add_many(self, data_list: Coroutine[Any, Any, List[COVIDReportData]]) -> Coroutine[Any, Any, List[COVIDReportData]]: # type: ignore[override]
        try:
            new_covid_report_records = self._covid_report_db_model.parse_many(
                data_list)
            await self._covid_report_db_model.insert_many(new_covid_report_records)
            return data_list
        except Exception as e:
            self._logger.error(
                "Fail to insert new covid_report records", exc_info=True)
            raise e

    async def get_one(self, id: str) -> COVIDReportData:
        try:
            covid_report_record = await self._covid_report_db_model.get_one({"covid_report_id": id})
            return self._covid_report_data_model.from_db_model(covid_report_record)
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve covid_report record of id {id}", exc_info=True)
            raise e

    async def get_many(self, query: dict) -> Coroutine[Any, Any, List[COVIDReportData]]: # type: ignore[override]
        try:
            covid_report_record = await self._covid_report_db_model.get(query)
            return [self._covid_report_data_model.from_db_model(record)
                    for record in covid_report_record]
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve covid_report records given query {query}", exc_info=True)
            raise e

    async def update_one(self, id: str, update_data: COVIDReportData) -> None:  # type: ignore[override]
        try:
            await self._covid_report_db_model.update_one(
                {"covid_report_id": id}, update_data.dict(exclude_unset=True))
        except Exception as e:
            self._logger.error(
                f"Fail to update covid_report record of id {id}", exc_info=True)
            raise e
        
    async def update_many(self, query: dict, data_list: List[COVIDReportData]) -> None: # type: ignore[override]
        pass

    async def delete_one(self, id: str) -> None:  # type: ignore[override]
        try:
            await self._covid_report_db_model.delete_one({"covid_report_id": id})
        except Exception as e:
            self._logger.error(
                f"Fail to delete covid_report record of id {id}", exc_info=True)
            raise e

    async def delete_many(self, query: dict) -> None: # type: ignore[override]
        try:
            await self._covid_report_db_model.delete_many(query)
        except Exception as e:
            self._logger.error(
                f"Fail to delete covid_report records given query {query}", exc_info=True)
            raise e


