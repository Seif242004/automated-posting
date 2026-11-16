from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import PostingRequest, PostingResponse
from app.services import posting_service

app = FastAPI(
    title="Automated Multi-Platform Posting",
    description="Publishes a short message with one CTA link to several platforms via their APIs.",
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]) or "body",
         "message": e["msg"].removeprefix("Value error, ")}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"success": False, "errors": errors})


@app.post("/posting", response_model=PostingResponse)
async def posting(req: PostingRequest) -> PostingResponse:
    return await posting_service.publish_everywhere(req.message, req.link)
