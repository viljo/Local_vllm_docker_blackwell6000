"""
FastAPI Router for Local LLM Service
Routes requests to appropriate vLLM backend based on model parameter
"""
import os
import logging
import time
import uuid
import subprocess
import asyncio
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
API_KEY = os.getenv("API_KEY", "sk-local-dev-key")
CODER_BACKEND_URL = os.getenv("CODER_BACKEND_URL", "http://vllm-coder:8000")
GENERAL_BACKEND_URL = os.getenv("GENERAL_BACKEND_URL", "http://vllm-general:8000")
GPT_OSS_120B_BACKEND_URL = os.getenv("GPT_OSS_120B_BACKEND_URL", "http://vllm-gpt-oss-120b:8000")
GPT_OSS_20B_BACKEND_URL = os.getenv("GPT_OSS_20B_BACKEND_URL", "http://vllm-gpt-oss-20b:8000")

# Model routing configuration
MODEL_ROUTING = {
    "deepseek-coder-33b-instruct": CODER_BACKEND_URL,
    "deepseek-coder-33B-instruct": CODER_BACKEND_URL,  # Case variation
    "mistral-7b-v0.1": GENERAL_BACKEND_URL,
    "qwen-2.5-14b-instruct": GENERAL_BACKEND_URL,
    "gpt-oss-120b": GPT_OSS_120B_BACKEND_URL,
    "gpt-oss-20b": GPT_OSS_20B_BACKEND_URL,
}

# Model name mapping (friendly name -> backend model name)
MODEL_NAME_MAPPING = {
    "deepseek-coder-33b-instruct": "TheBloke/deepseek-coder-33B-instruct-AWQ",
    "deepseek-coder-33B-instruct": "TheBloke/deepseek-coder-33B-instruct-AWQ",
    "mistral-7b-v0.1": "TheBloke/Mistral-7B-v0.1-AWQ",
    "qwen-2.5-14b-instruct": "TheBloke/Qwen2.5-14B-Instruct-AWQ",
    "gpt-oss-120b": "openai/gpt-oss-120b",
    "gpt-oss-20b": "openai/gpt-oss-20b",
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
    """Verify API key from Bearer token"""
    if credentials.credentials != API_KEY:
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
async def list_models(api_key: str = Depends(verify_api_key)):
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
    api_key: str = Depends(verify_api_key)
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
    api_key: str = Depends(verify_api_key)
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


# ============================================================================
# Model Management Endpoints (Dynamic Loading)
# ============================================================================

# Container name mapping
CONTAINER_NAMES = {
    "gpt-oss-120b": "vllm-gpt-oss-120b",
    "gpt-oss-20b": "vllm-gpt-oss-20b",
    "deepseek-coder-33b-instruct": "vllm-coder",
    "mistral-7b-v0.1": "vllm-general",
}

# Model metadata (sizes in GB, HuggingFace paths)
MODEL_METADATA = {
    "gpt-oss-120b": {
        "size_gb": 80,
        "hf_path": "openai/gpt-oss-120b",
        "description": "OpenAI GPT-OSS 120B - High reasoning model"
    },
    "gpt-oss-20b": {
        "size_gb": 16,
        "hf_path": "openai/gpt-oss-20b",
        "description": "OpenAI GPT-OSS 20B - Edge-optimized model"
    },
    "deepseek-coder-33b-instruct": {
        "size_gb": 19,
        "hf_path": "TheBloke/deepseek-coder-33B-instruct-AWQ",
        "description": "DeepSeek Coder 33B - Python specialist"
    },
    "mistral-7b-v0.1": {
        "size_gb": 4,
        "hf_path": "TheBloke/Mistral-7B-v0.1-AWQ",
        "description": "Mistral 7B - General purpose"
    },
}

async def run_docker_command(command: List[str]) -> tuple[bool, str]:
    """Execute docker command asynchronously"""
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        success = process.returncode == 0
        output = stdout.decode() if success else stderr.decode()
        return success, output
    except Exception as e:
        logger.error(f"Docker command failed: {e}")
        return False, str(e)


async def check_model_downloaded(hf_path: str) -> Dict[str, Any]:
    """Check if a HuggingFace model is downloaded"""
    # Check in the models/hub directory where HuggingFace caches models
    model_dir = f"/models/hub/models--{hf_path.replace('/', '--')}"
    success, output = await run_docker_command([
        "docker", "exec", "vllm-router", "sh", "-c", f"[ -d '{model_dir}' ] && echo 'true' || echo 'false'"
    ])

    is_downloaded = output.strip() == "true"

    if is_downloaded:
        # Try to get directory size
        success, size_output = await run_docker_command([
            "docker", "exec", "vllm-router", "du", "-sh", model_dir
        ])
        if success:
            size_str = size_output.split()[0] if size_output else "Unknown"
            return {"downloaded": True, "size": size_str}

    return {"downloaded": is_downloaded, "size": None}


async def get_container_status(container_name: str) -> Dict[str, Any]:
    """Get status of a Docker container"""
    # Get container state
    success, output = await run_docker_command([
        "docker", "inspect", "--format", "{{.State.Status}}", container_name
    ])

    if not success:
        return {"status": "not_found", "container": container_name}

    status = output.strip()
    result = {"status": status, "container": container_name}

    # If starting/restarting, check if it's loading
    if status == "running":
        # Check if container just started (less than 60 seconds ago)
        success, uptime = await run_docker_command([
            "docker", "inspect", "--format", "{{.State.StartedAt}}", container_name
        ])
        if success:
            from datetime import datetime
            try:
                started_at = datetime.fromisoformat(uptime.strip().replace('Z', '+00:00'))
                uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                if uptime_seconds < 60:
                    result["status"] = "loading"
            except:
                pass

    # Check for failed state
    if status == "exited":
        success, exit_code = await run_docker_command([
            "docker", "inspect", "--format", "{{.State.ExitCode}}", container_name
        ])
        if success and exit_code.strip() != "0":
            result["status"] = "failed"
            result["exit_code"] = exit_code.strip()

    return result


@app.get("/v1/models/status")
async def get_models_status(api_key: str = Depends(verify_api_key)):
    """Get status of all model backends with download info"""
    statuses = {}

    for model_name, container_name in CONTAINER_NAMES.items():
        container_status = await get_container_status(container_name)

        # Add model metadata
        metadata = MODEL_METADATA.get(model_name, {})
        container_status["size_gb"] = metadata.get("size_gb")
        container_status["description"] = metadata.get("description")

        # Check if model is downloaded
        hf_path = metadata.get("hf_path")
        if hf_path:
            download_info = await check_model_downloaded(hf_path)
            container_status["downloaded"] = download_info["downloaded"]
            container_status["downloaded_size"] = download_info["size"]

        # Check backend health if running (but not loading)
        if container_status["status"] == "running":
            backend_url = MODEL_ROUTING.get(model_name)
            if backend_url:
                health = await check_backend_health(backend_url)
                container_status["health"] = health.get("status", "unknown")

                # If health check fails, might still be loading
                if container_status["health"] != "healthy":
                    container_status["status"] = "loading"

        statuses[model_name] = container_status

    return {"models": statuses}


@app.post("/v1/models/{model_name}/start")
async def start_model(model_name: str, api_key: str = Depends(verify_api_key)):
    """Start a model backend container"""
    if model_name not in CONTAINER_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found. Available: {list(CONTAINER_NAMES.keys())}"
        )

    container_name = CONTAINER_NAMES[model_name]

    # Check current status
    status = await get_container_status(container_name)
    if status["status"] == "running":
        return {"message": f"Model '{model_name}' is already running", "status": "running"}

    # Start the container
    logger.info(f"Starting model '{model_name}' (container: {container_name})")
    success, output = await run_docker_command(["docker", "start", container_name])

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start model '{model_name}': {output}"
        )

    return {
        "message": f"Model '{model_name}' started successfully",
        "status": "starting",
        "container": container_name
    }


@app.post("/v1/models/{model_name}/stop")
async def stop_model(model_name: str, api_key: str = Depends(verify_api_key)):
    """Stop a model backend container"""
    if model_name not in CONTAINER_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found. Available: {list(CONTAINER_NAMES.keys())}"
        )

    container_name = CONTAINER_NAMES[model_name]

    # Check current status
    status = await get_container_status(container_name)
    if status["status"] in ["exited", "not_found"]:
        return {"message": f"Model '{model_name}' is not running", "status": status["status"]}

    # Stop the container
    logger.info(f"Stopping model '{model_name}' (container: {container_name})")
    success, output = await run_docker_command(["docker", "stop", container_name])

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop model '{model_name}': {output}"
        )

    return {
        "message": f"Model '{model_name}' stopped successfully",
        "status": "stopped",
        "container": container_name
    }


@app.post("/v1/models/{model_name}/restart")
async def restart_model(model_name: str, api_key: str = Depends(verify_api_key)):
    """Restart a model backend container"""
    if model_name not in CONTAINER_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found. Available: {list(CONTAINER_NAMES.keys())}"
        )

    container_name = CONTAINER_NAMES[model_name]

    logger.info(f"Restarting model '{model_name}' (container: {container_name})")
    success, output = await run_docker_command(["docker", "restart", container_name])

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart model '{model_name}': {output}"
        )

    return {
        "message": f"Model '{model_name}' restarted successfully",
        "status": "restarting",
        "container": container_name
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
