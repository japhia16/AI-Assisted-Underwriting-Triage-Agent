"""
FastAPI server for the Intake Agent.
Exposes endpoints for extraction only.
"""

from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uuid
import datetime
import io

import logging
import pypdf
from src.logging_utils import RequestIdFilter, set_request_id
from src.schemas import (
    ExtractRequest,
    ExtractResponse,
    MemoResponse,
    PricingHandoff,
    SubmissionJSON,
    GuardrailValidationError,
)
from src.intake_agent import process_request
from src.memo_agent import generate_underwriter_memo

# Configure logging: include request_id in log format via RequestIdFilter
LOG_FORMAT = "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)
# Attach RequestIdFilter to every root handler so the filter runs for records
# regardless of which child logger originated them.
root_logger = logging.getLogger()
for h in root_logger.handlers:
    h.addFilter(RequestIdFilter())

# Create FastAPI app
app = FastAPI(
    title="Insurance Intake Agent",
    description="Converts natural-language insurance requests into structured JSON.",
    version="1.0.0",
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Attach a request_id to each request and include it in responses."""
    req_id = uuid.uuid4().hex
    request.state.request_id = req_id
    # also set in contextvar for logging
    set_request_id(req_id)
    response = await call_next(request)
    # Expose request id to clients for tracing
    response.headers["X-Request-ID"] = req_id
    # clear contextvar after response
    set_request_id(None)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    payload = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": req_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    }
    return JSONResponse(payload, status_code=422)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    payload = {
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": detail,
            "request_id": req_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    }
    return JSONResponse(payload, status_code=exc.status_code)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    logger.error(f"Unhandled exception (request_id={req_id}): {exc}", exc_info=True)
    payload = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
            "request_id": req_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    }
    return JSONResponse(payload, status_code=500)


@app.exception_handler(GuardrailValidationError)
async def guardrail_exception_handler(request: Request, exc: GuardrailValidationError):
    req_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    payload = {
        "status": "error",
        "code": "GUARDRAIL_BREACH",
        "message": f"The pricing validation guardrail failed: {getattr(exc, 'message', str(exc))}",
        "request_id": req_id,
    }
    return JSONResponse(payload, status_code=422)


@app.post("/extract", response_model=ExtractResponse)
async def extract_request(request: ExtractRequest) -> ExtractResponse:
    try:
        result = process_request(request.text)
        response = ExtractResponse(**result)
        logger.info(f"Request processed successfully. Status: {response.status}")
        return response
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-memo", response_model=MemoResponse)
async def generate_memo(handoff: PricingHandoff) -> MemoResponse:
    try:
        memo = generate_underwriter_memo(handoff)
        logger.info("Underwriter memo generated successfully.")
        return memo
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected memo generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-submission", response_model=ExtractResponse)
async def upload_submission(file: UploadFile = File(...)) -> ExtractResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    try:
        contents = await file.read()
        pdf_stream = io.BytesIO(contents)
        reader = pypdf.PdfReader(pdf_stream)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        logger.error(f"PDF parsing failed: {exc}")
        raise HTTPException(status_code=400, detail="Failed to parse uploaded PDF.")

    result = process_request(extracted_text)
    response = ExtractResponse(**result)
    logger.info("PDF submission uploaded and extracted successfully.")
    return response


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"}, status_code=200)


@app.get("/")
async def root():
    return {
        "name": "Insurance Intake Agent",
        "version": "1.0.0",
        "description": "Converts natural-language insurance requests into structured JSON.",
        "endpoints": [
            {"method": "POST", "path": "/extract", "description": "Extract structured fields from text"},
            {"method": "POST", "path": "/generate-memo", "description": "Generate underwriting memo from extracted submission data"},
            {"method": "GET", "path": "/health", "description": "Health check"},
            {"method": "GET", "path": "/docs", "description": "Interactive API documentation (Swagger)"},
        ],
    }


# Pricing endpoints intentionally removed from public API surface.


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
