from fastapi import APIRouter, Depends, HTTPException
from ...models.response_models import Response
from ...models.data_models import JobData, SpecificationData
from typing import Optional
from dependency_injector.wiring import inject, Provide
from ...containers import Application
from ...service import (
    AsyncJobService,
    SpiderFactory,
    SpecificationService
)

job_controller = APIRouter()


@job_controller.get("/jobs", tags=["jobs"], response_model=Response[JobData])
@inject
async def read_jobs(query: Optional[str] = None,
                    limit: Optional[str] = None,
                    page: Optional[str] = None,
                    default_query: str = Depends(Provide[Application.config.api.default.query]),
                    default_limit: int = Depends(Provide[Application.config.api.default.limit.as_int()]),
                    default_page: int = Depends(Provide[Application.config.api.default.page.as_int()]),
                    job_service: AsyncJobService = Depends(Provide[Application.services.job_service])):
    query = query or default_query
    limit = limit or default_limit
    page = page or default_page

    skip = int(page) * int(limit) if int(page) > 0 else 0
    running_jobs = job_service.get_running_jobs(skip=skip, limit=int(limit))
    
    return Response[JobData](data=running_jobs)
        


@job_controller.post("/jobs", tags=["jobs"])
async def create_job(specification: SpecificationData,
                     spider_service_dispatcher: SpiderFactory = Provide[
                         Application.spider_services.spider_service_dispatcher],
                     spec_service: SpecificationService = Provide[Application.services.spec_service],
                     job_service: AsyncJobService = Depends(Provide[Application.services.job_service])):
    # read and validate specification
    try:
        job_spec = specification
        if specification.specification_id is None:
            # validate specification
            url_not_empty = len(specification.urls) > 0
            job_type_not_empty = specification.job_type is not None
            scrape_rules_not_empty = specification.scrape_rules is not None
            valid_input = url_not_empty and job_type_not_empty and scrape_rules_not_empty
            
            if not valid_input:
                raise HTTPException(
                    status_code=400,
                    detail="Field url, job_type and scrape_rules are required.")
            # save the new specification
            job_spec = await spec_service.add_one(job_spec)
        else:
            # user may pass an existing specification with id
            job_spec = await spec_service.get_one(str(specification.specification_id))
            
        spider_service = spider_service_dispatcher.spider_services[job_spec.job_type.value]
        crawl_task = spider_service.crawl(
            urls=job_spec.urls, rules=job_spec.scrape_rules)
        job_service.add_job(func=crawl_task, specification_id=job_spec.specification_id,
                            name=job_spec.job_name)
        
        # raise exception if not valid
        # get specified spider service from container
        # pass specification param to spider service
        # pass job and schedule to job service
        # return job creation status
        
        return {"username": "fakecurrentuser"}
    except Exception as e:
        raise e


@job_controller.delete("/jobs/{job_id}", tags=["jobs"])
async def read_user(job_id: str):
    return {"job_id": job_id}


@job_controller.put("/jobs", tags=["jobs"])
async def read_user(username: str):
    return {"username": username}

