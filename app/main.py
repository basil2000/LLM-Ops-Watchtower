"""
FastAPI main application with LLM chat endpoint and observability.
"""
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry import trace
from pydantic import BaseModel

import logging

from app import observability
from app.llm import GeminiClient
from app.logging_setup import setup_logging
from app.security import analyze_security

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Setup observability BEFORE creating the app
meter, tracer = observability.setup_observability()
app_metrics = observability.create_metrics(meter)

# Global clients
gemini_client: Optional[GeminiClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global gemini_client
    
    # Startup
    logger.info("Starting LLM Ops Watchtower application")
    
    # Initialize Gemini client
    try:
        gemini_client = GeminiClient()
        logger.info("Gemini client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
        # Allow app to start but requests will fail gracefully
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLM Ops Watchtower application")


# Create FastAPI app
app = FastAPI(
    title="LLM Ops Watchtower",
    description="LLM application with end-to-end observability for Datadog",
    version="1.0.0",
    lifespan=lifespan,
)

# Instrument FastAPI immediately after creation (before routes are registered)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
FastAPIInstrumentor.instrument_app(app)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    request_id: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the chat UI."""
    try:
        with open("static/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <head><title>LLM Ops Watchtower</title></head>
            <body>
                <h1>LLM Ops Watchtower</h1>
                <p>Static files not found. Please ensure static/index.html exists.</p>
            </body>
        </html>
        """


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req: Request,
    slow_mode: Optional[bool] = Query(None, description="Enable slow mode for testing"),
    simulate_failure: Optional[bool] = Query(None, description="Simulate a 500 error"),
):
    """
    Chat endpoint that processes messages through Gemini.
    
    Includes security checks, observability, and error handling.
    """
    request_start = time.time()
    request_id = str(uuid.uuid4())
    
    # Check for failure simulation
    if simulate_failure or os.getenv('ENABLE_FAILURE_MODE', 'false').lower() == 'true':
        logger.warning(f"Simulating failure for request {request_id}")
        app_metrics.get('failures', None) and app_metrics['failures'].add(1, {})
        raise HTTPException(status_code=500, detail="Simulated failure for testing")
    
    # Get or create root span
    try:
        with tracer.start_as_current_span("chat.request") as root_span:
            # Security analysis
            with tracer.start_as_current_span("security.check") as security_span:
                security_result = analyze_security(request.message)
                
                # Record security findings in span attributes
                security_span.set_attribute("security.prompt_injection", security_result['prompt_injection'])
                security_span.set_attribute("security.pii_detected", security_result['pii_detected'])
                security_span.set_attribute("security.prompt_hash", security_result['prompt_hash'])
                security_span.set_attribute("security.pii_types", str(security_result['pii_types']))
                
                # Update metrics
                if security_result['prompt_injection']:
                    app_metrics.get('prompt_injection_count', None) and app_metrics['prompt_injection_count'].add(1, {})
                
                if security_result['pii_detected']:
                    app_metrics.get('pii_leak_count', None) and app_metrics['pii_leak_count'].add(1, {})
                    for pii_type, count in security_result['pii_types'].items():
                        app_metrics.get('pii_leak_count', None) and app_metrics['pii_leak_count'].add(count, {'pii_type': pii_type})
            
            # Slow mode simulation
            slow_mode_delay = 0
            if slow_mode or os.getenv('ENABLE_SLOW_MODE', 'false').lower() == 'true':
                slow_mode_delay = int(os.getenv('SLOW_MODE_DELAY_MS', '1000'))
                if slow_mode_delay > 0:
                    time.sleep(slow_mode_delay / 1000.0)
                    logger.info(f"Slow mode delay: {slow_mode_delay}ms", extra={"request_id": request_id})
            
            # Check if Gemini client is available
            if not gemini_client:
                root_span.set_status(trace.Status(trace.StatusCode.ERROR, "Gemini client not available"))
                raise HTTPException(
                    status_code=503,
                    detail="LLM service is not available. Check your Google Cloud configuration."
                )
            
            # Call LLM
            response_text = ""
            token_counts = {'tokens_in': 0, 'tokens_out': 0}
            llm_latency_ms = 0.0
            
            with tracer.start_as_current_span("llm.request") as llm_span:
                try:
                    response_text, token_counts, llm_latency_ms = gemini_client.generate(
                        request.message,
                        request_id
                    )
                    
                    # Set span attributes
                    llm_span.set_attribute("llm.model", gemini_client.model_name)
                    llm_span.set_attribute("llm.tokens_in", token_counts['tokens_in'])
                    llm_span.set_attribute("llm.tokens_out", token_counts['tokens_out'])
                    llm_span.set_attribute("llm.latency_ms", llm_latency_ms)
                    
                    # Update metrics
                    app_metrics.get('llm_latency', None) and app_metrics['llm_latency'].record(
                        llm_latency_ms, {}
                    )
                    app_metrics.get('tokens_in', None) and app_metrics['tokens_in'].add(
                        token_counts['tokens_in'], {}
                    )
                    app_metrics.get('tokens_out', None) and app_metrics['tokens_out'].add(
                        token_counts['tokens_out'], {}
                    )
                    
                except Exception as e:
                    llm_span.record_exception(e)
                    llm_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    app_metrics.get('failures', None) and app_metrics['failures'].add(1, {})
                    logger.error(
                        f"LLM generation failed: {e}",
                        extra={"request_id": request_id},
                        exc_info=True
                    )
                    raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
            
            # Calculate total request latency
            total_latency_ms = (time.time() - request_start) * 1000
            
            # Set root span attributes
            root_span.set_attribute("http.method", "POST")
            root_span.set_attribute("http.route", "/chat")
            root_span.set_attribute("session_id", request.session_id)
            root_span.set_attribute("request_id", request_id)
            root_span.set_attribute("llm.model", gemini_client.model_name)
            root_span.set_attribute("request.latency_ms", total_latency_ms)
            root_span.set_attribute("security.prompt_injection", security_result['prompt_injection'])
            root_span.set_attribute("security.pii_detected", security_result['pii_detected'])
            root_span.set_attribute("security.prompt_hash", security_result['prompt_hash'])
            root_span.set_attribute("llm.tokens_in", token_counts['tokens_in'])
            root_span.set_attribute("llm.tokens_out", token_counts['tokens_out'])
            
            # Update request metrics
            app_metrics.get('request_count', None) and app_metrics['request_count'].add(1, {})
            app_metrics.get('request_latency', None) and app_metrics['request_latency'].record(
                total_latency_ms, {}
            )
            
            # Log request completion
            logger.info(
                "Request completed successfully",
                extra={
                    "request_id": request_id,
                    "session_id": request.session_id,
                    "model": gemini_client.model_name,
                    "latency_ms": total_latency_ms,
                    "llm_latency_ms": llm_latency_ms,
                    "tokens_in": token_counts['tokens_in'],
                    "tokens_out": token_counts['tokens_out'],
                    "prompt_injection": security_result['prompt_injection'],
                    "pii_detected": security_result['pii_detected'],
                    "pii_types": security_result['pii_types'],
                    "prompt_hash": security_result['prompt_hash'],
                    "prompt_preview": security_result['prompt_preview'],
                }
            )
            
            return ChatResponse(
                response=response_text,
                request_id=request_id
            )
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        app_metrics.get('failures', None) and app_metrics['failures'].add(1, {})
        raise
    except Exception as e:
        # Handle unexpected errors
        total_latency_ms = (time.time() - request_start) * 1000
        app_metrics.get('failures', None) and app_metrics['failures'].add(1, {})
        
        logger.error(
            f"Unexpected error in chat endpoint: {e}",
            extra={"request_id": request_id},
            exc_info=True
        )
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "llm-ops-watchtower",
        "gemini_available": gemini_client is not None,
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )

