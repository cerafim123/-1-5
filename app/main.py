import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth_router, directory_router, router
from app.database import engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Заявки УК API",
    summary="REST API приложения для заявок жильцов управляющей компании",
    description=(
        "API поддерживает регистрацию и вход пользователей, "
        "управление заявками и получение справочных данных "
        "с разграничением доступа по ролям."
    ),
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Авторизация",
            "description": "Регистрация, вход и сведения о текущем пользователе",
        },
        {
            "name": "Заявки",
            "description": "Создание, просмотр, изменение и удаление заявок",
        },
        {
            "name": "Справочники",
            "description": "Получение домов, квартир и мастеров",
        },
        {
            "name": "Состояние",
            "description": "Проверка доступности сервера и базы данных",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)
app.include_router(directory_router)

def problem_response(
    request: Request,
    status_code: int,
    title: str,
    detail,
    type_uri: str = "about:blank",
):
    content = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
    }
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(content),
        media_type="application/problem+json",
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Content",
        503: "Service Unavailable",
    }
    response = problem_response(
        request=request,
        status_code=exc.status_code,
        title=titles.get(exc.status_code, "Request Error"),
        detail=exc.detail,
    )

    if exc.headers:
        response.headers.update(exc.headers)

    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return problem_response(
        request=request,
        status_code=422,
        title="Unprocessable Content",
        detail=exc.errors(),
    )

@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception("Непредвиденная ошибка API")
    return problem_response(
        request=request,
        status_code=500,
        title="Internal Server Error",
        detail="Внутренняя ошибка сервера",
    )

@app.get(
    "/",
    tags=["Состояние"],
    summary="Информация об API",
)
def root():
    return {"message": "API приложения «Заявки УК» работает"}

@app.get(
    "/health",
    tags=["Состояние"],
    summary="Проверка подключения к MySQL",
    responses={
        503: {"description": "База данных недоступна"},
    },
)
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError as error:
        logger.exception("Ошибка подключения к базе данных")
        raise HTTPException(status_code=503,
            detail="Нет подключения к базе данных MySQL",
        ) from error
