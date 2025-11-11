"""
FastAPI Router for Local LLM Service
Routes requests to appropriate vLLM backend based on model parameter
"""
import os
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import httpx

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.getenv("API_KEY")
if not API_KEY or API_KEY == "sk-local-dev-key":
    logger.error("API_KEY environment variable must be set to a secure value")
    logger.error("Generate one with: python3 -c \"import secrets; print('sk-local-' + secrets.token_hex(32))\"")
    raise ValueError("API_KEY must be set to a secure value")

CODER_BACKEND_URL = os.getenv("CODER_BACKEND_URL", "http://vllm-coder:8000")
GENERAL_BACKEND_URL = os.getenv("GENERAL_BACKEND_URL", "http://vllm-general:8000")

# WebUI authentication - allow requests from WebUI without API key for local service
# For remote access scenarios, you may want to implement session-based auth or IP whitelisting
WEBUI_AUTH_ENABLED = os.getenv("WEBUI_AUTH_ENABLED", "false").lower() == "true"

# Model routing configuration
MODEL_ROUTING = {
    "deepseek-coder-33b-instruct": CODER_BACKEND_URL,
    "deepseek-coder-33B-instruct": CODER_BACKEND_URL,  # Case variation
    "mistral-7b-v0.1": GENERAL_BACKEND_URL,
    "qwen-2.5-14b-instruct": GENERAL_BACKEND_URL,
}

# Model name mapping (friendly name -> backend model name)
MODEL_NAME_MAPPING = {
    "deepseek-coder-33b-instruct": "TheBloke/deepseek-coder-33B-instruct-AWQ",
    "deepseek-coder-33B-instruct": "TheBloke/deepseek-coder-33B-instruct-AWQ",
    "mistral-7b-v0.1": "TheBloke/Mistral-7B-v0.1-AWQ",
    "qwen-2.5-14b-instruct": "TheBloke/Qwen2.5-14B-Instruct-AWQ",
}

# HTTP client for backend requests
http_client: Optional[httpx.AsyncClient] = None

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global http_client

    # Startup
    logger.info("Starting router service")
    logger.info(f"Coder backend: {CODER_BACKEND_URL}")
    logger.info(f"General backend: {GENERAL_BACKEND_URL}")

    http_client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout for long generations

    yield

    # Shutdown
    logger.info("Shutting down router service")
    await http_client.aclose()


# Create FastAPI app
app = FastAPI(
    title="Local LLM Service Router",
    description="OpenAI-compatible API router for local vLLM backends",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - allow all origins for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Reduced to force more frequent preflight checks
)

# Additional middleware to ensure CORS headers on all responses
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response


# ============================================================================
# Authentication
# ============================================================================

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify API key from Bearer token using constant-time comparison"""
    import secrets
    if not secrets.compare_digest(credentials.credentials, API_KEY):
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid API key provided",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key"
                }
            }
        )
    return credentials.credentials


def optional_verify_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> str:
    """
    Verify API key but allow requests without auth from trusted sources (WebUI).
    This implements a Backend-for-Frontend (BFF) pattern where the WebUI can access
    the router without exposing the API key in the browser.

    For local services, this is acceptable. For production/public services,
    implement proper session-based auth or IP whitelisting.
    """
    # If credentials are provided, verify them
    if credentials:
        import secrets
        if secrets.compare_digest(credentials.credentials, API_KEY):
            return credentials.credentials
        else:
            logger.warning(f"Invalid API key attempt from {request.client.host}")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "message": "Invalid API key provided",
                        "type": "invalid_request_error",
                        "code": "invalid_api_key"
                    }
                }
            )

    # If WEBUI_AUTH_ENABLED is True, require authentication
    if WEBUI_AUTH_ENABLED:
        logger.warning(f"Missing API key from {request.client.host}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "API key required",
                    "type": "invalid_request_error",
                    "code": "missing_api_key"
                }
            }
        )

    # Allow unauthenticated access for local WebUI
    logger.debug(f"Allowing unauthenticated request from {request.client.host}")
    return "webui-access"


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    stop: Optional[List[str]] = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "vllm"
    status: str = "ready"


class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# ============================================================================
# Utility Functions
# ============================================================================

def get_backend_url(model: str) -> str:
    """Route model to appropriate backend"""
    backend_url = MODEL_ROUTING.get(model.lower())
    if not backend_url:
        # Try partial match
        for model_key, url in MODEL_ROUTING.items():
            if model_key in model.lower() or model.lower() in model_key:
                backend_url = url
                break

    if not backend_url:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Model '{model}' not found. Available models: {list(MODEL_ROUTING.keys())}",
                    "type": "invalid_request_error",
                    "code": "model_not_found"
                }
            }
        )

    return backend_url


async def check_backend_health(backend_url: str) -> Dict[str, Any]:
    """Check if backend is healthy and ready"""
    try:
        response = await http_client.get(f"{backend_url}/health", timeout=5.0)
        return {"status": "healthy" if response.status_code == 200 else "unhealthy"}
    except Exception as e:
        logger.error(f"Backend health check failed for {backend_url}: {e}")
        return {"status": "unhealthy", "error": str(e)}


# ============================================================================
# Health Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Basic health check - returns 200 if router is responding"""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness():
    """
    Readiness check - returns 200 when at least one backend model is ready
    Aggregates health from both backends
    """
    coder_health = await check_backend_health(CODER_BACKEND_URL)
    general_health = await check_backend_health(GENERAL_BACKEND_URL)

    models_status = {
        "deepseek-coder-33b-instruct": coder_health.get("status", "unhealthy"),
        "mistral-7b-v0.1": general_health.get("status", "unhealthy"),
    }

    # At least one model must be healthy
    if any(status == "healthy" for status in models_status.values()):
        return {"status": "ready", "models": models_status}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "models": models_status}
        )


# ============================================================================
# OpenAI-Compatible Endpoints
# ============================================================================

@app.get("/v1/models")
async def list_models(request: Request, api_key: str = Depends(optional_verify_api_key)):
    """List available models"""
    models = []

    # Check which backends are available
    coder_health = await check_backend_health(CODER_BACKEND_URL)
    general_health = await check_backend_health(GENERAL_BACKEND_URL)

    if coder_health["status"] == "healthy":
        models.append(ModelInfo(
            id="deepseek-coder-33b-instruct",
            created=int(time.time()),
            status="ready"
        ))

    if general_health["status"] == "healthy":
        models.append(ModelInfo(
            id="mistral-7b-v0.1",
            created=int(time.time()),
            status="ready"
        ))

    return ModelList(data=models)


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(optional_verify_api_key)
):
    """
    Create chat completion - routes to appropriate backend based on model
    Supports both streaming and non-streaming responses
    """
    request_id = str(uuid.uuid4())
    client_ip = raw_request.client.host

    logger.info(
        f"[{request_id}] Chat completion request - "
        f"model={request.model}, stream={request.stream}, "
        f"messages={len(request.messages)}, client={client_ip}"
    )

    # Route to appropriate backend
    backend_url = get_backend_url(request.model)
    logger.info(f"[{request_id}] Routing to backend: {backend_url}")

    # Forward request to backend
    backend_endpoint = f"{backend_url}/v1/chat/completions"

    try:
        # Prepare request payload and translate model name to backend model name
        payload = request.model_dump(exclude_none=True)
        backend_model = MODEL_NAME_MAPPING.get(request.model, request.model)
        payload["model"] = backend_model

        if request.stream:
            # Streaming response
            async def stream_generator():
                async with http_client.stream(
                    "POST",
                    backend_endpoint,
                    json=payload,
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    timeout=300.0
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"[{request_id}] Backend error: {error_text}")
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=error_text.decode()
                        )

                    async for chunk in response.aiter_text():
                        yield chunk

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming response
            response = await http_client.post(
                backend_endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=300.0
            )

            if response.status_code != 200:
                logger.error(f"[{request_id}] Backend error: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json()
                )

            logger.info(f"[{request_id}] Request completed successfully")
            return response.json()

    except httpx.TimeoutException:
        logger.error(f"[{request_id}] Backend timeout")
        raise HTTPException(
            status_code=504,
            detail={
                "error": {
                    "message": "Backend request timed out",
                    "type": "server_error",
                    "code": "timeout"
                }
            }
        )
    except httpx.ConnectError:
        logger.error(f"[{request_id}] Cannot connect to backend")
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": f"Backend service unavailable: {backend_url}",
                    "type": "service_unavailable",
                    "code": "backend_unavailable"
                }
            }
        )
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Internal server error",
                    "type": "server_error",
                    "code": "internal_error"
                }
            }
        )


# ============================================================================
# Legacy Completions Endpoint (optional)
# ============================================================================

@app.post("/v1/completions")
async def completions(
    raw_request: Request,
    api_key: str = Depends(optional_verify_api_key)
):
    """
    Legacy completions endpoint - converts to chat format and routes
    """
    request_data = await raw_request.json()
    request_id = str(uuid.uuid4())

    logger.info(f"[{request_id}] Legacy completion request - model={request_data.get('model')}")

    # Convert to chat format
    prompt = request_data.get("prompt", "")
    if isinstance(prompt, list):
        prompt = "\n".join(prompt)

    chat_request = ChatCompletionRequest(
        model=request_data.get("model"),
        messages=[ChatMessage(role="user", content=prompt)],
        stream=request_data.get("stream", False),
        max_tokens=request_data.get("max_tokens"),
        temperature=request_data.get("temperature", 1.0),
        top_p=request_data.get("top_p", 1.0),
    )

    # Use chat completions endpoint
    return await chat_completions(chat_request, raw_request, api_key)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
