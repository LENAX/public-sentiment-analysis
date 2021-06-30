from fastapi import APIRouter

job_controller = APIRouter()


@job_controller.get("/jobs/", tags=["jobs"])
async def read_jobs():
    return [{"username": "Rick"}, {"username": "Morty"}]


@job_controller.post("/jobs", tags=["jobs"])
async def create_job():
    return {"username": "fakecurrentuser"}


@job_controller.delete("/jobs/{job_id}", tags=["jobs"])
async def read_user(job_id: str):
    return {"job_id": job_id}


@job_controller.put("/users/{username}", tags=["jobs"])
async def read_user(username: str):
    return {"username": username}

