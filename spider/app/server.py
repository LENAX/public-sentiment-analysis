from os import getenv
from aiohttp import ClientSession, client_exceptions
from fastapi import BackgroundTasks, Depends,  FastAPI, HTTPException
from datetime import datetime
from .enums import JobStatus
from .models.request_models import ResultQuery, JobSpecification
from .models.response_models import (
    JobCreationResponse,
    JobResultResponse,
    ResultQueryResponse,
    SinglePageResponse
)
from .models.data_models import (
    URL,
    JobCreationStatus,
    JobResult,
    HTMLData,
    RequestHeader
)
from .config import config
from .service import HTMLSpiderService

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    def create_http_session():
        return ClientSession(headers=config['headers'])

    app.client_session = create_http_session()


@app.on_event("shutdown")
async def shutdown_event():
    await app.client_session.close()


@app.get("/")
async def welcome():
    return {"message": "Welcome to sentiment analysis! I am a little spider."}


@app.get("/html", response_model=HTMLData)
async def get_single_page(url: str):
    """ Get a single page for testing purposes.
    """
    
    html_spider = HTMLSpiderService(
        session=app.client_session, html_data_mapper=None)
    try:
        html = await html_spider.get(data_src=URL(url=url))
    except client_exceptions.InvalidURL as e:
        raise HTTPException(status_code=400, detail=f"Invalid url {e}. Missing 'http://'?")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"{e}")
    
    return HTMLData(html=html)


@app.post("/new-job", response_model=JobCreationStatus)
async def create_new_job(job: JobSpecification, background_tasks: BackgroundTasks):
    # TODO: refactor the instantiation using DI
    html_spider = HTMLSpiderService(
        session=app.client_session, html_data_mapper=None)
    background_tasks.add_task(
        html_spider.get_many, data_src=job.urls)
    return JobCreationStatus(job_id="aaa",
                             create_dt=datetime.now(),
                             specification=job)


@app.get("/result/{job_id}")
async def get_result_by_id(job_id: str):
    return JobResultResponse(
            job_result=JobResult(
                job_id=job_id,
                status=JobStatus.DONE,
                message="ok",
                data=HTMLData(
                    html="<html></html>",
                    domain="http://foobar.com",
                    keywords=["foo"]
                )
            ),
            status_code=200,
            message="success").dict()


@app.post("/result/new-query")
async def query_result(query: ResultQuery):
    return ResultQueryResponse(
        data=[
            HTMLData(
                html="<html></html>",
                domain="http://foobar.com",
                keywords=["foo"]
            ),
            HTMLData(
                html="<p>bar</p>",
                domain="http://foobar.com.cn",
                keywords=["bar"]
            )
        ],
        query=query,
        status_code=200,
        message="success").dict()
