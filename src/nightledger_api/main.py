from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nightledger_api.controllers.events_controller import router as events_router
from nightledger_api.presenters.error_presenter import (
    present_authorize_action_request_validation_error,
    present_ambiguous_event_id_error,
    present_approval_not_found_error,
    present_business_rule_validation_error,
    present_duplicate_approval_error,
    present_duplicate_event_error,
    present_inconsistent_run_state_error,
    present_no_pending_approval_error,
    present_approval_request_validation_error,
    present_run_not_found_error,
    present_schema_validation_error,
    present_storage_read_error,
    present_storage_write_error,
    present_execution_action_mismatch_error,
    present_execution_decision_not_approved_error,
    present_execution_token_expired_error,
    present_execution_token_invalid_error,
    present_execution_token_missing_error,
    present_execution_token_replayed_error,
)
from nightledger_api.services.errors import (
    AmbiguousEventIdError,
    ApprovalNotFoundError,
    BusinessRuleValidationError,
    DuplicateApprovalError,
    DuplicateEventError,
    InconsistentRunStateError,
    NoPendingApprovalError,
    RunNotFoundError,
    SchemaValidationError,
    StorageReadError,
    StorageWriteError,
    ExecutionActionMismatchError,
    ExecutionDecisionNotApprovedError,
    ExecutionTokenExpiredError,
    ExecutionTokenInvalidError,
    ExecutionTokenMissingError,
    ExecutionTokenReplayedError,
)


HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", None)
if HTTP_422_UNPROCESSABLE is None:
    HTTP_422_UNPROCESSABLE = status.HTTP_422_UNPROCESSABLE_ENTITY
SCHEMA_VALIDATION_STATUS_CODE = HTTP_422_UNPROCESSABLE


app = FastAPI(title="NightLedger API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(events_router)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    if request.method == "POST" and request.url.path == "/v1/mcp/authorize_action":
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE,
            content=present_authorize_action_request_validation_error(exc),
        )
    if request.method == "POST" and request.url.path.startswith("/v1/approvals/"):
        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE,
            content=present_approval_request_validation_error(exc),
        )
    return await request_validation_exception_handler(request, exc)


@app.exception_handler(SchemaValidationError)
async def handle_schema_validation_error(
    request: Request, exc: SchemaValidationError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE,
        content=present_schema_validation_error(exc),
    )


@app.exception_handler(BusinessRuleValidationError)
async def handle_business_rule_validation_error(
    request: Request, exc: BusinessRuleValidationError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=present_business_rule_validation_error(exc),
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


@app.exception_handler(RunNotFoundError)
async def handle_run_not_found_error(
    request: Request, exc: RunNotFoundError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=present_run_not_found_error(exc),
    )


@app.exception_handler(InconsistentRunStateError)
async def handle_inconsistent_run_state_error(
    request: Request, exc: InconsistentRunStateError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=present_inconsistent_run_state_error(exc),
    )


@app.exception_handler(ApprovalNotFoundError)
async def handle_approval_not_found_error(
    request: Request, exc: ApprovalNotFoundError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=present_approval_not_found_error(exc),
    )


@app.exception_handler(AmbiguousEventIdError)
async def handle_ambiguous_event_id_error(
    request: Request, exc: AmbiguousEventIdError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=present_ambiguous_event_id_error(exc),
    )


@app.exception_handler(NoPendingApprovalError)
async def handle_no_pending_approval_error(
    request: Request, exc: NoPendingApprovalError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=present_no_pending_approval_error(exc),
    )


@app.exception_handler(DuplicateApprovalError)
async def handle_duplicate_approval_error(
    request: Request, exc: DuplicateApprovalError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=present_duplicate_approval_error(exc),
    )


@app.exception_handler(ExecutionTokenMissingError)
async def handle_execution_token_missing_error(
    request: Request, exc: ExecutionTokenMissingError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=present_execution_token_missing_error(exc),
    )


@app.exception_handler(ExecutionTokenInvalidError)
async def handle_execution_token_invalid_error(
    request: Request, exc: ExecutionTokenInvalidError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=present_execution_token_invalid_error(exc),
    )


@app.exception_handler(ExecutionTokenExpiredError)
async def handle_execution_token_expired_error(
    request: Request, exc: ExecutionTokenExpiredError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=present_execution_token_expired_error(exc),
    )


@app.exception_handler(ExecutionTokenReplayedError)
async def handle_execution_token_replayed_error(
    request: Request, exc: ExecutionTokenReplayedError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=present_execution_token_replayed_error(exc),
    )


@app.exception_handler(ExecutionActionMismatchError)
async def handle_execution_action_mismatch_error(
    request: Request, exc: ExecutionActionMismatchError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=present_execution_action_mismatch_error(exc),
    )


@app.exception_handler(ExecutionDecisionNotApprovedError)
async def handle_execution_decision_not_approved_error(
    request: Request, exc: ExecutionDecisionNotApprovedError
) -> JSONResponse:
    _ = request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=present_execution_decision_not_approved_error(exc),
    )
