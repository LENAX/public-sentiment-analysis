from fastapi import APIRouter

result_controller = APIRouter()


@result_controller.get("/results/", tags=["results"])
async def read_results():
    return [{"username": "Rick"}, {"username": "Morty"}]


@result_controller.post("/results", tags=["results"])
async def create_result():
    return {"username": "fakecurrentuser"}


@result_controller.delete("/results/{result_id}", tags=["results"])
async def delete_result(result_id: str):
    return {"result_id": result_id}


