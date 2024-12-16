import uuid

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import ORJSONResponse

from app.api.email.router import router as email_router
from conf import DOCS_TITLE, DOCS_VERSION

app = FastAPI(
    default_response_class=ORJSONResponse,
    title=DOCS_TITLE,
    version=DOCS_VERSION,
)

# Add the custom middleware to the app
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Middleware to automatically generate and attach a unique request ID to each HTTP
    request and response.

    Summary:
    This middleware intercepts incoming HTTP requests and generates a unique
    UUID-based request ID. The ID is attached to the `request.state` object, allowing
    it to be accessed within the application. After processing the request, the
    middleware also adds the generated request ID to the response headers for tracking
    purposes.

    :param request: Incoming HTTP request object to be processed.
    :type request: starlette.requests.Request
    :param call_next: Asynchronous function to proceed with the next middleware or
        endpoint and obtain a response.
    :type call_next: Callable[[starlette.requests.Request],
        Awaitable[starlette.responses.Response]]
    :return: Processed HTTP response with injected request ID in its headers.
    :rtype: starlette.responses.Response
    """
    request_id = str(uuid.uuid4())

    # Attach the request_id to the request state
    request.state.request_id = request_id

    # Proceed with the request and get the response
    response: Response = await call_next(request)

    # inject the request_id into the response headers
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(
    router=email_router,
)

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
