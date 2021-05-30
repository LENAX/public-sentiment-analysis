from aiohttp import ClientSession, client_exceptions
from fastapi import BackgroundTasks, FastAPI, HTTPException
from datetime import datetime
from .enums import JobState
from .models.request_models import ResultQuery, JobSpecification
from .models.response_models import (
    JobResultResponse,
    ResultQueryResponse
)
from .models.data_models import (
    URL,
    JobStatus,
    JobResult,
    HTMLData
)
from .config import config
from .service import HTMLSpiderService
from .db import create_client

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    def create_http_session():
        return ClientSession(headers=config['headers'])

    app.client_session = create_http_session()
    app.db_client = create_client(**config['db'])


@app.on_event("shutdown")
async def shutdown_event():
    await app.client_session.close()
    await app.db_client.close()


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


@app.post("/new-job", response_model=JobStatus)
async def create_new_job(job: JobSpecification, background_tasks: BackgroundTasks):
    """ Create a new job and start immediately
    
    High level business logic:
    1. create a job according to the given specification
    2. create a spider according to the job type
    3. initiate a background task
    4. return a JobStatus object
    """
    # High level business logic:

    
    # TODO: create spider based on given job specification
    html_spider = HTMLSpiderService(
        session=app.client_session, html_data_mapper=None)
    background_tasks.add_task(
        html_spider.get_many, data_src=job.urls)
    return JobStatus(job_id="aaa",
                             create_dt=datetime.now(),
                             specification=job)


@app.get("/result/{job_id}")
async def get_result_by_id(job_id: str):
    """ Get the scrape result given job id
    """
    # TODO: paging, html string truncation, job status query

    return JobResultResponse(
            job_result=JobResult(
                job_id=job_id,
                status=JobState.DONE,
                message="ok",
                data=HTMLData(
                    url=URL(url="http://foobar.com"),
                    html="<html></html>",
                    job_id=job_id,
                    create_dt=datetime.now(),
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
