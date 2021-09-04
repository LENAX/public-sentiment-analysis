import uvicorn
import time
from fastapi import FastAPI, Request
from ...common.models.db_models import bind_db_to_all_models
from ...config import config
from .container import Application

import logging

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
server_logger = logging.getLogger(__name__)
server_logger.setLevel(logging.DEBUG)


def create_app() -> FastAPI:
    container = Application()
    container.config.from_dict(config)

    db_client = container.resources.db_client()
    bind_db_to_all_models(db_client, config['db']['db_name'])

    app = FastAPI()
    app.container = container

    return app


app = create_app()


@app.on_event("startup")
async def startup_event():
    logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    server_logger.info(f"start request path={request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    server_logger.info(
        f"completed_in={formatted_process_time}ms status_code={response.status_code}")

    return response


@app.get("/")
async def welcome():
    return {"message": "Hello! I am a little spider who can fetch weather forecast."}


if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    uvicorn.run(app, log_config=log_config)
