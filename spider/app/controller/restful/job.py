from fastapi import APIRouter, Depends, HTTPException
from ...models.response_models import Response
from ...models.data_models import (
    JobData, SpecificationData, Schedule, JobStatus)
from typing import Optional
from dependency_injector.wiring import inject, Provide
from ...containers import Application
from ...service import (
    AsyncJobService,
    SpiderFactory,
    SpecificationService
)

import logging

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
job_logger = logging.getLogger(__name__)
job_logger.setLevel(logging.DEBUG)


job_controller = APIRouter()


@job_controller.get("/jobs", tags=["jobs"], response_model=Response[JobData])
@inject
async def get_jobs(query: Optional[str] = None,
                   limit: Optional[str] = None,
                   page: Optional[str] = None,
                   default_query: str = Depends(Provide[Application.config.api.default.query]),
                   default_limit: int = Depends(Provide[Application.config.api.default.limit.as_int()]),
                   default_page: int = Depends(Provide[Application.config.api.default.page.as_int()]),
                   job_service: AsyncJobService = Depends(Provide[Application.services.job_service])):    
    try:
        query = query or default_query
        limit = limit or default_limit
        page = page or default_page
        
        job_logger.info(f"In get jobs..., query: {query}, limit: {limit}, page: {page}")

        skip = int(page) * int(limit) if int(page) > 0 else 0
        running_jobs = job_service.get_running_jobs(skip=skip, limit=int(limit))
        
        job_logger.info(
            f"Got jobs {running_jobs}")
        
        return Response[JobData](data=running_jobs)
    except Exception as e:
        job_logger.error(f"In get jobs, Error: {e}")
        return Response(error=str(e))

@job_controller.post("/jobs", tags=["jobs"], response_model=Response[JobData])
@inject
async def create_job(specification: SpecificationData,
                     spider_service_dispatcher: SpiderFactory = Provide[
                         Application.spider_services.spider_service_dispatcher],
                     spec_service: SpecificationService = Provide[Application.services.spec_service],
                     job_service: AsyncJobService = Depends(Provide[Application.services.job_service])):
    # read and validate specification
    try:
        job_logger.info(
            f"In create_job..., specification: {specification}")
        
        spec = specification
        if specification.specification_id is None:
            job_logger.info("Create a job specification...")
            # validate specification
            url_not_empty = len(specification.urls) > 0
            job_spec_not_empty = specification.job_spec is not None
            job_type_not_empty = job_spec_not_empty and specification.job_spec.job_type is not None
            scrape_rules_not_empty = specification.scrape_rules is not None
            valid_input = (url_not_empty and 
                           job_spec_not_empty and
                           job_type_not_empty and
                           scrape_rules_not_empty)
            
            if not valid_input:
                job_logger.error(
                    f"In create_job..., input is invalid."
                    f"url_not_empty: {url_not_empty}"
                    f"job_spec_not_empty: {job_spec_not_empty}"
                    f"job_type_not_empty: {job_type_not_empty}"
                    f"valid_input: {valid_input}")
                raise HTTPException(
                    status_code=400,
                    detail="Field url, job_type and scrape_rules are required.")
            
            job_logger.info("Saving job specification...")
            
            # save the new specification
            spec = await spec_service.add_one(spec)
            
            job_logger.info("Job specification saved.")
        else:
            job_logger.info("Fetching existing job specification...")
            # user may pass an existing specification with id
            spec = await spec_service.get_one(str(specification.specification_id))
            job_logger.info(f"Fetched job specification: {spec}")
            
        job_spec = spec.job_spec
        spider_service = spider_service_dispatcher.spider_services[job_spec.job_type.value]
        
        job_logger.info(f"Use spider {spider_service}")
        
        crawl_task = spider_service.crawl(urls=spec.urls, rules=spec.scrape_rules)
        created_job = await job_service.add_job(func=crawl_task, schedule=job_spec.schedule,
                                                specification_id=spec.specification_id,
                                                name=job_spec.name)
        
        job_logger.info(f"Created job {created_job}")
        
        return Response[JobData](data=created_job)
    except Exception as e:
        job_logger.error(f"In create_job, Error: {e}")
        return Response(error=str(e))


@job_controller.delete("/jobs/{job_id}", tags=["jobs"], response_model=Response[str])
@inject
async def delete_job(job_id: str,
                     job_service: AsyncJobService = Depends(Provide[Application.services.job_service])):
    try:
        job_logger.info(
            f"In delete_job..., job_id: {job_id}")
        await job_service.delete_job(job_id)
        return Response[str](data="ok")
    except Exception as e:
        job_logger.error(f"In delete_job, Error: {e}")
        return Response(error=str(e))


@job_controller.put("/jobs/{job_id}/schedule", tags=["jobs"], response_model=Response[str])
async def update_job_schedule(job_id: str,
                              schedule: Schedule,
                              job_service: AsyncJobService = Depends(Provide[Application.services.job_service])):
    """Update job by specification

    Supports changing the schedule of a job
    """
    try:
        job_logger.info(
            f"job_id: {job_id}, schedule: {schedule}")
        
        await job_service.update_job(job_id, schedule=schedule)
        job_logger.info("Job update succeed!")
        return Response[str](data='ok')
    except Exception as e:
        job_logger.error(f"Error: {e}")
        return Response(error=str(e))


@job_controller.put("/jobs/{job_id}/status", tags=["jobs"], response_model=Response[str])
async def update_job_status(job_id: str,
                            status: JobStatus,
                            job_service: AsyncJobService = Depends(Provide[Application.services.job_service])):
    """Update job by specification

    Supports changing the schedule of a job
    """
    try:
        job_logger.info(
            f"job_id: {job_id}, schedule: {status}")

        await job_service.update_job(job_id, status=status)
        job_logger.info("Job status update succeed!")
        return Response[str](data='ok')
    except Exception as e:
        job_logger.error(f"Error: {e}")
        return Response(error=str(e))
