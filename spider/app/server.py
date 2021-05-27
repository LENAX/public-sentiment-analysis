from fastapi import FastAPI
from datetime import datetime
from .enums import JobStatus
from .models.request_models import ResultQuery, JobSpecification
from .models.response_models import (
    JobCreationResponse,
    JobResultResponse,
    ResultQueryResponse
)
from .models.data_models import (
    JobCreationStatus,
    JobResult,
    HTMLData
)


app = FastAPI()


@app.get("/")
async def welcome():
    return {"message": "Welcome to sentiment analysis! I am a little spider."}


@app.get("/html")
async def get_single_page(url: str):
    """ Get a single page for testing purposes.
    """
    return {'url': url}


@app.post("/new-job")
async def create_new_job(job: JobSpecification):
    return JobCreationResponse(
            creation_status=JobCreationStatus(
                job_id="aaa",
                create_dt=datetime.now(),
                specification=job
            ),
            status_code=200,
            message="success").dict()


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
