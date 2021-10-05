from typing import Optional

from fastapi import FastAPI

sentry_sdk.init(
    dsn=config.SENTRY_DNS,
    traces_sample_rate=1,
    environment=config.ENV.name,
    integrations=[
        ExcepthookIntegration(),
        AtexitIntegration(),
        DedupeIntegration(),
        StdlibIntegration(),
    ],
)

app.add_middleware(SentryAsgiMiddleware)


# This middleware prevents the app running asynchronously 
@app.middleware("http")
async def sentry_exception(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except BaseException as e:
        session_user = request.session.get("user")
        if session_user:
            db = next(get_db())
            user = crud.user.get(db, id=session_user.get("username")).one()
            sentry_sdk.set_user({"id": user.id, "email": user.email})
            company_id = session_user.get("company_id")
            if company_id:
                company = crud.company.get(db, id=company_id).one_or_none()
                sentry_sdk.set_tag("company_name", company.name)
                sentry_sdk.set_tag("company_id", company.id)
        sentry_sdk.capture_exception(e)
        raise e

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}
