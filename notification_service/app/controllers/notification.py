from fastapi import APIRouter, Depends
from ..models.response_models import Response
from ..models.data_models import Notification
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import HappyPAICNotificationService, SubscriptionService
import traceback
import logging
from logging import Logger

def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    notification_logger = logging.getLogger(__name__)
    notification_logger.setLevel(logging.DEBUG)
    return notification_logger


notification_controller = APIRouter()


@notification_controller.post('/notification/group-message', tags=["notification"])
@inject
async def send_group_message(message: Notification,
                             subscription_service: SubscriptionService = Depends(Provide[
                                 Application.services.subscription_service]),
                             notification_service: HappyPAICNotificationService = Depends(Provide[
                                 Application.services.happy_paic_notification_service]),
                             notification_logger: Logger = Depends(create_logger)):
    try:
        subscribers = await subscription_service.get_many({'service_name': message.sender})
        send_succeeded = await notification_service.send_to_group(
            notification=message.body,
            group=[subscriber.subscriber_id for subscriber in subscribers
                   if subscriber.subscriber_id is not None])
        
        if send_succeeded:
            return Response(message="ok", statusCode=200, status="success")
        else:
            return Response(message="failed to send message", statusCode=400, status="failed"), 400
        
    except Exception as e:
        traceback.print_exc()
        notification_logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500


@notification_controller.post('/notification/private-message', tags=["notification"])
@inject
async def send_private_message(message: Notification,
                               notification_service: HappyPAICNotificationService = Depends(Provide[
                                   Application.services.happy_paic_notification_service]),
                               notification_logger: Logger = Depends(create_logger)):
    try:
        if message.receiver is None:
            return Response(message="The receiver must be specified.",
                            statusCode=400, status="failed"), 400
        
        send_succeeded = await notification_service.send(
            notification=message.body,
            receiver=message.receiver)

        if send_succeeded:
            return Response(message="ok", statusCode=200, status="success")
        else:
            return Response(message=f"failed to send message to {message.receiver}",
                            statusCode=400, status="failed"), 400

    except Exception as e:
        traceback.print_exc()
        notification_logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500

