from typing import Optional

import asyncio

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from sentry_sdk.integrations.stdlib import StdlibIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.atexit import AtexitIntegration

def before_send(event, hint):
    print(event['user'])
    return None

sentry_sdk.init(
    dsn="",
    traces_sample_rate=1,
    # before_send=before_send,
    debug=True,
    integrations=[
        ExcepthookIntegration(),
        AtexitIntegration(),
        DedupeIntegration(),
        StdlibIntegration(),
    ],
)

app = FastAPI(debug=True)

# This middleware prevents the app running asynchronously 
@app.middleware("http")
async def sentry_exception(request, call_next):
    try:
        response = await call_next(request)
        return response
    except BaseException as e:
        session_user = request.session.get("user")
        if session_user:
            # db = next(get_db())
            # user = crud.user.get(db, id=session_user.get("username")).one()
            sentry_sdk.set_user({"id": "advanced-user-id-123", "email": "user@example.org"})
            # company_id = session_user.get("company_id")
            # if company_id:
                # company = crud.company.get(db, id=company_id).one_or_none()
            sentry_sdk.set_tag("company_name", "name")
            sentry_sdk.set_tag("company_id", "id")
        sentry_sdk.capture_exception(e)
        raise e

class DoNothingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request, call_next
    ):
        response = await call_next(request)
        return response

async def background_task(text: str, seconds: int):
    print(f"Task {text} started")
    await asyncio.sleep(seconds)
    l = 5 / 0
    print(f"Task {text} ended")

# if you add this middleware then requests are getting blocked
# app.add_middleware(DoNothingMiddleware)

@app.get("/run", status_code=status.HTTP_200_OK)
async def test(background_tasks: BackgroundTasks, text: str = "Test", secs: int = 10):
    background_tasks.add_task(background_task, text, secs)
    return {"text": text, "secs": secs}

app.add_middleware(SentryAsgiMiddleware)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, e):
    with sentry_sdk.configure_scope() as scope:
        scope.set_context("request", request)
        sentry_sdk.capture_exception(e)

    return await http_exception_handler(request, e)

@app.get("/")
async def read_root():
    # raise HTTPException(status_code=418, detail="Nope! I don't like it")
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    # l = 5 / 0
    return {"item_id": item_id, "q": q}
