from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from nightledger_api.controllers.events_controller import router as events_router
from nightledger_api.presenters.error_presenter import (
    present_schema_validation_error,
)
from nightledger_api.services.errors import SchemaValidationError

app = FastAPI(title="NightLedger API", version="0.1.0")
app.include_router(events_router)


@app.exception_handler(SchemaValidationError)
async def handle_schema_validation_error(
    request: Request, exc: SchemaValidationError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=present_schema_validation_error(exc),
    )
