from fastapi import FastAPI, HTTPException
from .db import create_client
from .models.db_models import bind_db_to_all_models
from .controller.restful import job_controller, result_controller
from .config import config

import logging

logging.basicConfig()
server_logger = logging.getLogger(__name__)
server_logger.setLevel(logging.DEBUG)


def create_app() -> FastAPI:
    container = Container()
    container.config.from_yaml('config.yml')
    container.config.giphy.api_key.from_env('GIPHY_API_KEY')
    container.wire(modules=[endpoints])

    app = FastAPI()
    app.container = container
    app.include_router(endpoints.router)
    return app


app = create_app()
app.include_router(job_controller)
app.include_router(result_controller)

@app.on_event("startup")
async def startup_event():
    server_logger.info("Starting up server...")
    
    db_config = config['db']
    db_client = create_client(
        host=db_config['host'],
        username=db_config['username'],
        password=db_config['password'],
        port=db_config['port'],
        db_name=db_config['db_name'])
    bind_db_to_all_models(db_client, db_config['db_name'])


@app.on_event("shutdown")
async def shutdown_event():
    pass


@app.get("/")
async def welcome():
    return {"message": "Welcome to sentiment analysis! I am a little spider."}

