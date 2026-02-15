from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from nightledger_api.controllers.events_controller import router as events_router
from nightledger_api.presenters.error_presenter import (
    present_duplicate_event_error,
    present_schema_validation_error,
    present_storage_read_error,
    present_storage_write_error,
)
from nightledger_api.services.errors import (
    DuplicateEventError,
    SchemaValidationError,
    StorageReadError,
    StorageWriteError,
)


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


@app.exception_handler(StorageWriteError)
async def handle_storage_write_error(
    request: Request, exc: StorageWriteError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=present_storage_write_error(exc),
    )


@app.exception_handler(StorageReadError)
async def handle_storage_read_error(
    request: Request, exc: StorageReadError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=present_storage_read_error(exc),
    )


@app.exception_handler(DuplicateEventError)
async def handle_duplicate_event_error(
    request: Request, exc: DuplicateEventError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=present_duplicate_event_error(exc),
    )

