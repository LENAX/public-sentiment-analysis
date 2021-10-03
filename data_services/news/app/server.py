import uvicorn
import random
import string
import time
from fastapi import FastAPI, Request
from .models.db_models import bind_db_to_all_models
from .controllers import news, theme, word_cloud
from .config import config
from .container import Application

import logging

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
server_logger = logging.getLogger(__name__)
server_logger.setLevel(logging.DEBUG)


def create_app() -> FastAPI:
    container = Application()
    container.config.from_dict(config)
    container.wire(modules=[news, theme, word_cloud])

    db_client = container.resources.db_client()
    bind_db_to_all_models(db_client, config['db']['db_name'])

    app = FastAPI()
    app.container = container
    app.include_router(news.news_controller)
    app.include_router(theme.theme_controller)
    app.include_router(word_cloud.word_cloud_controller)
    
    return app


app = create_app()


@app.on_event("startup")
async def startup_event():
    logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)



@app.get("/")
async def welcome():
    return {"message": "I am a news monitor service!"}


if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s | %(levelname)s | %(funcName)s | %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s | %(levelname)s | %(funcName)s | %(message)s"
    uvicorn.run(app, log_config=log_config, port=8082)
