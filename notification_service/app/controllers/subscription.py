from fastapi import APIRouter, Depends
from ..models.response_models import Response
from ..models.data_models import Subscription
from ..models.db_models import SubscriptionDBModel
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import SubscriptionService
import traceback
import logging
from logging import Logger


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    subscription_logger = logging.getLogger(__name__)
    subscription_logger.setLevel(logging.DEBUG)
    return subscription_logger


subscription_controller = APIRouter()


@subscription_controller.get('/notification/subscribers', tags=["notification-subscription"], response_model=Response[Subscription])
@inject
async def get_subscribers(service_name: str, subscriber_id: Optional[str],
                          subscriber_id_type: Optional[str], name: Optional[str],
                          subscription_service: SubscriptionService = Depends(Provide[
                                 Application.services.subscription_service]),
                          subscription_logger: Logger = Depends(create_logger)):
    try:
        required_args = {'service_name': service_name}
        optional_args = {'subscriber_id': subscriber_id,
                         'subscriber_id_type': subscriber_id_type,
                         'name': name}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        subscribers = await subscription_service.get_many(query)
        return Response[Subscription](data=[Subscription.parse_obj(sub) for sub in subscribers],
                                      message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        subscription_logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500


@subscription_controller.post('/notification/subscribers', tags=["notification-subscription"], response_model=Response)
@inject
async def add_new_subscription(new_subscribers: List[Subscription],
                               subscription_service: SubscriptionService = Depends(Provide[
                                   Application.services.subscription_service]),
                               subscription_logger: Logger = Depends(create_logger)):
    try:
        if len(new_subscribers) == 0:
            return Response(message="You must provide at least one subscriber.",
                            statusCode=400, status="failed"), 400

        await subscription_service.add_many(new_subscribers)

        return Response(message="ok", statusCode=200, status="success")
    except Exception as e:
        traceback.print_exc()
        subscription_logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500


@subscription_controller.put('/notification/subscribers', tags=["notification-subscription"], response_model=Response)
@inject
async def update_subscribers(service_name: str, subscriber_id: Optional[str],
                             subscriber_id_type: Optional[str], name: Optional[str],
                             subscriber_data: Subscription,
                             subscription_service: SubscriptionService = Depends(Provide[
                                 Application.services.subscription_service]),
                             subscription_logger: Logger = Depends(create_logger)):
    try:
        required_args = {'service_name': service_name}
        optional_args = {'subscriber_id': subscriber_id,
                         'subscriber_id_type': subscriber_id_type,
                         'name': name}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        await subscription_service.update_many(query, subscriber_data.dict())
        return Response(message="ok", statusCode=200, status="success")
    except Exception as e:
        traceback.print_exc()
        subscription_logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500


@subscription_controller.delete('/notification/subscribers', tags=["notification-subscription"], response_model=Response[Subscription])
@inject
async def delete_subscribers(service_name: str, subscriber_id: Optional[str],
                             subscriber_id_type: Optional[str], name: Optional[str],
                             subscription_service: SubscriptionService = Depends(Provide[
                              Application.services.subscription_service]),
                             subscription_logger: Logger = Depends(create_logger)):
    try:
        required_args = {'service_name': service_name}
        optional_args = {'subscriber_id': subscriber_id,
                         'subscriber_id_type': subscriber_id_type,
                         'name': name}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        await subscription_service.delete_many(query)
        return Response(message="ok", statusCode=200, status="success")
    except Exception as e:
        traceback.print_exc()
        subscription_logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500


