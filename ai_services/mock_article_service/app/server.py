import logging
import time

import uvicorn
from ai_services.mock_article_service.app.models.base import Response
from ai_services.mock_article_service.app.models.request_models import \
    ArticleServiceArgs
from ai_services.mock_article_service.app.models.response_models import (
    ArticleCategory, ArticlePopularity, ArticleSummary)
from fastapi import FastAPI, Request

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
server_logger = logging.getLogger(__name__)
server_logger.setLevel(logging.DEBUG)


def create_app() -> FastAPI:
    app = FastAPI()

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
    return {"message": "Hello! I am a fake ai."}


@app.post("/content-abstract", response_model=Response[ArticleSummary])
def generate_abstract(args: ArticleServiceArgs):
    return Response(data=ArticleSummary(abstract_result=f"{args.content[:100]}..."), statusCode=200, status="success", message="ok")


@app.post("/article-popularity", response_model=Response[ArticlePopularity])
def generate_popularity(args: ArticleServiceArgs):
    return Response(data=ArticlePopularity(sim_result=1, hot_value=1), statusCode=200, status="success", message="ok")


@app.post("/article-category", response_model=Response[ArticleCategory])
def generate_category(args: ArticleServiceArgs):
    return Response(data=ArticleCategory(whether_medical_result=1), statusCode=200, status="success", message="ok")


if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    uvicorn.run(app, log_config=log_config, port=9000)
