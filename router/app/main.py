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
from pydantic import BaseModel, Field, ConfigDict
import httpx
from typing import Union

# Tool calling modules
from .transformations import (
    inject_tools_into_messages,
    transform_response_with_tools,
    validate_tool_result_messages,
    create_error_response
)
from .tool_parsing import (
    generate_tool_call_id,
    extract_tool_calls_from_text,
    validate_tool_exists
)
from .streaming import (
    stream_with_tool_detection,
    simple_stream_passthrough
)

# Configure logging with enhanced format
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Add detailed format for ERROR level
class DetailedErrorFormatter(logging.Formatter):
    """Custom formatter that adds extra detail for error logs"""

    def format(self, record):
        # Standard format for non-errors
        if record.levelno < logging.ERROR:
            return super().format(record)

        # Enhanced format for errors with more context
        result = super().format(record)

        # Add exception info if available
        if record.exc_info:
            result += f"\nException: {record.exc_info[0].__name__}"

        return result

# Configure root logger
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler()
    ]
)

# Get logger and set custom formatter
logger = logging.getLogger(__name__)
for handler in logging.getLogger().handlers:
    handler.setFormatter(DetailedErrorFormatter(LOG_FORMAT))

# Log startup
logger.info(f"Starting vLLM Router - Log Level: {LOG_LEVEL}")

# Configuration
API_KEY = os.getenv("API_KEY", "sk-local-dev-key")
CODER_BACKEND_URL = os.getenv("CODER_BACKEND_URL", "http://vllm-coder:8000")
GENERAL_BACKEND_URL = os.getenv("GENERAL_BACKEND_URL", "http://vllm-general:8000")
GPT_OSS_120B_BACKEND_URL = os.getenv("GPT_OSS_120B_BACKEND_URL", "http://vllm-gpt-oss-120b:8000")
GPT_OSS_20B_BACKEND_URL = os.getenv("GPT_OSS_20B_BACKEND_URL", "http://vllm-gpt-oss-20b:8000")
DOCKER_COMPOSE_FILE = os.getenv("DOCKER_COMPOSE_FILE", "/docker-compose.yml")
HOST_PROJECT_DIR = os.getenv("HOST_PROJECT_DIR", "/home/asvil/git/local_llm_service")  # Fallback for local dev

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

    # Wait for Docker network to be ready
    await asyncio.sleep(5)

    # Auto-start the largest downloaded model at startup
    logger.info("Auto-starting largest downloaded model at startup...")

    # Check which models are downloaded
    downloaded_models = []
    for model_name, metadata in MODEL_METADATA.items():
        hf_path = metadata.get('hf_path')
        if hf_path:
            download_info = await check_model_downloaded(hf_path)
            if download_info.get('downloaded'):
                downloaded_models.append((model_name, metadata['gpu_memory_gb']))
                logger.info(f"  {model_name}: Downloaded ({metadata['gpu_memory_gb']}GB)")
            else:
                logger.info(f"  {model_name}: Not downloaded")

    if downloaded_models:
        # Start the largest downloaded model with smart memory management
        largest_model = max(downloaded_models, key=lambda x: x[1])
        model_name, required_memory_gb = largest_model

        logger.info(f"Auto-starting {model_name} ({required_memory_gb}GB GPU memory)...")

        try:
            # Check if already running
            container_name = CONTAINER_NAMES.get(model_name)
            if not container_name:
                logger.warning(f"No container mapping found for {model_name}")
            else:
                status = await get_container_status(container_name)

                if status["status"] == "running":
                    logger.info(f"{model_name} is already running")
                else:
                    # First check if there are running containers to unload
                    all_containers = await run_docker_command(["docker", "ps", "--format", "{{.Names}}"])
                    running_model_containers = []

                    if all_containers[0]:  # success
                        for line in all_containers[1].strip().split('\n'):
                            if line.startswith('vllm-') and line != container_name:
                                # Find model name for this container
                                for m_name, c_name in CONTAINER_NAMES.items():
                                    if c_name == line:
                                        m_metadata = MODEL_METADATA.get(m_name, {})
                                        running_model_containers.append({
                                            "name": m_name,
                                            "container": c_name,
                                            "gpu_memory_gb": m_metadata.get("gpu_memory_gb", 0)
                                        })
                                        break

                    # If there are running containers, stop them first
                    should_start = True
                    if running_model_containers:
                        logger.info(f"Found {len(running_model_containers)} running model(s), unloading before auto-start...")
                        # Sort by GPU memory (largest first)
                        running_model_containers.sort(key=lambda m: m["gpu_memory_gb"], reverse=True)

                        for model in running_model_containers:
                            logger.info(f"Stopping {model['name']} ({model['gpu_memory_gb']}GB)")
                            await run_docker_command(["docker", "stop", model['container']])

                        # Wait and verify GPU memory is actually released
                        logger.info("Waiting for GPU memory to be released...")
                        max_wait_cycles = 20  # 20 * 3 seconds = 60 seconds max
                        for i in range(max_wait_cycles):
                            await asyncio.sleep(3)
                            gpu_info = await get_gpu_memory_info()
                            available_gb = gpu_info["available_gb"]
                            logger.info(f"  Check {i+1}/{max_wait_cycles}: {available_gb:.2f}GB free")

                            if available_gb >= required_memory_gb:
                                logger.info(f"✓ Sufficient memory available: {available_gb:.2f}GB >= {required_memory_gb}GB")
                                break
                        else:
                            # Timeout reached - check if we have enough anyway
                            if available_gb < required_memory_gb:
                                logger.error(f"Timeout waiting for memory release. Available: {available_gb:.2f}GB < Required: {required_memory_gb}GB. Skipping auto-start.")
                                should_start = False
                    else:
                        # No running containers, but still check available memory
                        gpu_info = await get_gpu_memory_info()
                        available_gb = gpu_info["available_gb"]
                        logger.info(f"No running models found. Available memory: {available_gb:.2f}GB, Required: {required_memory_gb}GB")

                        if available_gb < required_memory_gb:
                            logger.error(f"Insufficient GPU memory for {model_name}. Need {required_memory_gb}GB but only {available_gb:.2f}GB available. Skipping auto-start.")
                            should_start = False

                    # Now start the model if we have enough memory
                    if not should_start:
                        logger.warning(f"Skipping auto-start of {model_name} due to insufficient memory")
                    else:
                        profile = CONTAINER_PROFILES.get(container_name)
                        project_dir = os.path.dirname(DOCKER_COMPOSE_FILE)
                        compose_cmd_base = ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "-p", "local-llm-service"]
                        if profile:
                            compose_cmd_base.extend(["--profile", profile])

                        compose_env = {"PWD": HOST_PROJECT_DIR}
                        success, output = await run_docker_command(
                            compose_cmd_base + ["up", "-d", container_name],
                            cwd=project_dir,
                            env=compose_env
                        )

                        if success:
                            logger.info(f"Successfully started {model_name}")
                        else:
                            logger.error(f"Failed to start {model_name}: {output}")
        except Exception as e:
            logger.error(f"Error during auto-start: {e}")
    else:
        logger.warning("No downloaded models found, skipping auto-start")

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

# Exception handler for validation errors (422)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log and return detailed validation errors"""
    error_details = exc.errors()
    logger.error(f"Validation error for {request.method} {request.url.path}")
    logger.error(f"Client: {request.client.host if request.client else 'unknown'}")
    logger.error(f"Validation errors: {error_details}")

    # Return OpenAI-compatible error response
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "Invalid request parameters",
                "type": "invalid_request_error",
                "code": "validation_error",
                "param": error_details[0]["loc"][-1] if error_details else None,
                "details": error_details
            }
        }
    )

# CORS configuration - allow all origins for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
    max_age=600,  # Reduced to force more frequent preflight checks
)

# Additional middleware to ensure CORS headers on all responses
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
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
    model_config = ConfigDict(extra='allow')

    role: str = Field(..., pattern="^(system|user|assistant|tool)$")
    # Support both string and array content (OpenAI Vision API format)
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class ToolFunction(BaseModel):
    """Function definition for tool calling"""
    model_config = ConfigDict(extra='allow')

    name: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    description: Optional[str] = None
    parameters: Dict[str, Any]
    strict: Optional[bool] = False


class Tool(BaseModel):
    """Tool definition with function specification"""
    model_config = ConfigDict(extra='allow')

    type: str = "function"
    function: ToolFunction


class ChatCompletionRequest(BaseModel):
    """Chat completion request with tool calling support"""
    model_config = ConfigDict(extra='allow')  # Accept unknown parameters

    model: str
    messages: List[ChatMessage]
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    stop: Optional[Union[str, List[str]]] = None

    # Tool calling parameters (NEW)
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = None
    stream_options: Optional[Dict[str, Any]] = None


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

@app.get("/v1/api/info")
async def get_api_info():
    """Get API connection information - no auth required for UI display"""
    router_port = os.getenv("ROUTER_PORT", "8080")
    return {
        "api_key": API_KEY,
        "router_port": router_port,
    }


@app.get("/v1/models")
async def list_models(api_key: str = Depends(verify_api_key)):
    """List available models - only returns running and healthy models"""
    models = []

    # Get status of all models
    statuses = await get_models_status(api_key)
    all_models = statuses.get("models", {})

    # Only include models that are running and healthy
    for model_name, status in all_models.items():
        if status.get("status") == "running" and status.get("health") == "healthy":
            models.append(ModelInfo(
                id=model_name,
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
        f"messages={len(request.messages)}, tools={len(request.tools or [])}, "
        f"max_tokens={request.max_tokens}, "
        f"client={client_ip}"
    )

    # Route to appropriate backend
    backend_url = get_backend_url(request.model)
    logger.info(f"[{request_id}] Routing to backend: {backend_url}")

    # Forward request to backend
    backend_endpoint = f"{backend_url}/v1/chat/completions"

    try:
        # Validate tool result messages if present
        messages_for_validation = [
            msg.model_dump() if hasattr(msg, 'model_dump') else msg
            for msg in request.messages
        ]

        if request.tools and any(msg.get('role') == 'tool' for msg in messages_for_validation):
            try:
                validate_tool_result_messages(messages_for_validation)
            except ValueError as e:
                logger.error(f"[{request_id}] Tool validation error: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=create_error_response(
                        message=str(e),
                        error_type="invalid_request_error",
                        code="invalid_tool_call_id"
                    )
                )

        # Transform request: inject tools into messages if tools are provided
        messages = inject_tools_into_messages(request.messages, request.tools)

        # Prepare request payload and translate model name to backend model name
        payload = request.model_dump(exclude_none=True)
        payload["messages"] = messages
        backend_model = MODEL_NAME_MAPPING.get(request.model, request.model)
        payload["model"] = backend_model

        # Remove tool-calling parameters that backend doesn't support
        payload.pop("tools", None)
        payload.pop("tool_choice", None)
        payload.pop("parallel_tool_calls", None)
        payload.pop("stream_options", None)

        # Handle max_tokens: if None, set a reasonable default
        # vLLM can calculate negative max_tokens if prompt is too long and max_tokens=None
        if payload.get("max_tokens") is None:
            # Set a reasonable default that leaves room for the prompt
            default_max_tokens = 4096
            payload["max_tokens"] = default_max_tokens
            logger.info(f"[{request_id}] max_tokens not specified, using default: {default_max_tokens}")

        # Log payload being sent to backend (for debugging)
        logger.info(f"[{request_id}] Sending to backend - max_tokens={payload.get('max_tokens')}")

        if request.stream:
            # Streaming response with tool detection and usage stats
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

                    # Use enhanced streaming if tools are present or usage stats requested
                    if request.tools or (request.stream_options and request.stream_options.get("include_usage")):
                        async for chunk in stream_with_tool_detection(
                            response.aiter_text(),
                            request,
                            backend_model
                        ):
                            yield chunk
                    else:
                        # Simple passthrough for non-tool requests
                        async for chunk in simple_stream_passthrough(response.aiter_text()):
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

            # Transform response to inject tool_calls if detected
            backend_response = response.json()
            transformed_response = transform_response_with_tools(backend_response, request)

            logger.info(f"[{request_id}] Request completed successfully")
            return transformed_response

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
    except HTTPException:
        # Re-raise HTTPException without modification (for validation errors, etc.)
        raise
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

# Docker Compose profiles for each container
CONTAINER_PROFILES = {
    "vllm-gpt-oss-120b": "gpt-oss-120b",
    "vllm-gpt-oss-20b": "gpt-oss-20b",
    "vllm-coder": "deepseek-coder",
    "vllm-general": "mistral",
}

# Model metadata (GPU memory requirements based on --gpu-memory-utilization settings)
# GPU Total: ~95.6GB, each model reserves: total_gpu * utilization_factor
# Reserved memory includes: model weights + KV cache + activations + overhead
MODEL_METADATA = {
    "gpt-oss-120b": {
        "gpu_memory_gb": 81,  # 95.6GB * 0.85 utilization (model: 122GB disk, MXFP4 quantized in memory)
        "disk_size_gb": 183,  # Disk size for reference
        "hf_path": "openai/gpt-oss-120b",
        "description": "GPT-OSS 120B - Advanced reasoning (117B params, 5.1B active)",
        "load_time_seconds": 61  # From benchmark
    },
    "gpt-oss-20b": {
        "gpu_memory_gb": 19,  # 95.6GB * 0.20 utilization (model: 26GB disk, MXFP4 quantized in memory)
        "disk_size_gb": 40,
        "hf_path": "openai/gpt-oss-20b",
        "description": "GPT-OSS 20B - Efficient reasoning (21B params, 3.6B active)",
        "load_time_seconds": 15  # Estimated
    },
    "deepseek-coder-33b-instruct": {
        "gpu_memory_gb": 43,  # 95.6GB * 0.45 utilization (model: 17GB + KV cache: 26GB)
        "disk_size_gb": 43,
        "hf_path": "TheBloke/deepseek-coder-33B-instruct-AWQ",
        "description": "DeepSeek Coder 33B - Python specialist",
        "load_time_seconds": 20  # Estimated
    },
    "mistral-7b-v0.1": {
        "gpu_memory_gb": 10,  # 95.6GB * 0.10 utilization (model: 4GB + KV cache: 5.5GB + overhead)
        "disk_size_gb": 7,
        "hf_path": "TheBloke/Mistral-7B-v0.1-AWQ",
        "description": "Mistral 7B - General purpose",
        "load_time_seconds": 8  # Estimated
    },
}

async def run_docker_command(command: List[str], cwd: str = None, env: Dict[str, str] = None) -> tuple[bool, str]:
    """Execute docker command asynchronously"""
    try:
        logger.info(f"Executing docker command: {' '.join(command)}" + (f" (cwd={cwd})" if cwd else "") + (f" (env={env})" if env else ""))

        # Merge custom env with current environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=process_env
        )
        stdout, stderr = await process.communicate()

        success = process.returncode == 0
        output = stdout.decode() if success else stderr.decode()
        return success, output
    except Exception as e:
        logger.error(f"Docker command failed: {e}")
        return False, str(e)


async def check_model_downloaded(hf_path: str) -> Dict[str, Any]:
    """Check if a HuggingFace model is fully downloaded"""
    # Check in the models/hub directory where HuggingFace caches models
    model_dir = f"/models/hub/models--{hf_path.replace('/', '--')}"
    success, output = await run_docker_command([
        "docker", "exec", "vllm-router", "sh", "-c", f"[ -d '{model_dir}' ] && echo 'true' || echo 'false'"
    ])

    if output.strip() != "true":
        return {"downloaded": False, "downloading": False, "size": None}

    # Check if download is complete by looking at .no_exist directory
    # Only check for essential files - ignore optional ones like preprocessor_config.json, video_preprocessor_config.json, etc.
    success, no_exist_files = await run_docker_command([
        "docker", "exec", "vllm-router", "sh", "-c",
        f"find '{model_dir}/.no_exist' -type f -name '*.safetensors' -o -name 'config.json' 2>/dev/null"
    ])

    is_downloading = False
    is_fully_downloaded = False

    if success:
        # Only consider model as incomplete if essential files (weights, config) are missing
        has_essential_missing = bool(no_exist_files.strip())
        if has_essential_missing:
            is_downloading = True  # Essential files still downloading
            is_fully_downloaded = False
        else:
            is_downloading = False
            is_fully_downloaded = True  # Essential files complete (optional files don't matter)
    else:
        # If .no_exist doesn't exist at all, assume download is complete
        is_fully_downloaded = True

    # Get directory size
    success, size_output = await run_docker_command([
        "docker", "exec", "vllm-router", "du", "-sh", model_dir
    ])
    size_str = size_output.split()[0] if success and size_output else None

    return {
        "downloaded": is_fully_downloaded,
        "downloading": is_downloading,
        "size": size_str
    }


async def get_gpu_memory_info() -> dict:
    """Get current GPU memory usage using nvidia-smi"""
    try:
        # Try to exec nvidia-smi from running GPU containers first
        gpu_containers = ["vllm-gpt-oss-120b", "vllm-coder", "vllm-general", "vllm-gpt-oss-20b"]

        for container in gpu_containers:
            success, output = await run_docker_command([
                "docker", "exec", container, "nvidia-smi",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits"
            ])

            if success and output.strip():
                used, total = output.strip().split(", ")
                return {
                    "used_mb": int(used),
                    "total_mb": int(total),
                    "available_mb": int(total) - int(used),
                    "used_gb": round(int(used) / 1024, 2),
                    "total_gb": round(int(total) / 1024, 2),
                    "available_gb": round((int(total) - int(used)) / 1024, 2)
                }

        # If no containers are running, use a temporary container
        logger.info("No running GPU containers found, using temporary container for GPU memory check")
        success, output = await run_docker_command([
            "docker", "run", "--rm", "--gpus", "all",
            "nvidia/cuda:12.1.0-base-ubuntu22.04",
            "nvidia-smi", "--query-gpu=memory.used,memory.total",
            "--format=csv,noheader,nounits"
        ])

        if success and output.strip():
            used, total = output.strip().split(", ")
            return {
                "used_mb": int(used),
                "total_mb": int(total),
                "available_mb": int(total) - int(used),
                "used_gb": round(int(used) / 1024, 2),
                "total_gb": round(int(total) / 1024, 2),
                "available_gb": round((int(total) - int(used)) / 1024, 2)
            }
    except Exception as e:
        logger.error(f"Failed to get GPU memory: {e}")
    return {"used_gb": 0, "total_gb": 0, "available_gb": 0}


async def get_container_gpu_memory(container_name: str) -> float:
    """Get GPU memory used by a specific container in GB"""
    try:
        # Check container is running
        success, status = await run_docker_command([
            "docker", "inspect", "--format", "{{.State.Status}}", container_name
        ])
        if not success or status.strip() != "running":
            return 0.0

        # Get GPU memory from container
        success, output = await run_docker_command([
            "docker", "exec", container_name, "nvidia-smi",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits"
        ])
        if success and output.strip():
            used_mb = int(output.strip())
            return round(used_mb / 1024, 1)
    except Exception as e:
        logger.debug(f"Could not get GPU memory for {container_name}: {e}")
    return 0.0


async def get_container_status(container_name: str) -> Dict[str, Any]:
    """Get status of a Docker container"""
    from datetime import datetime

    # Get container state
    success, output = await run_docker_command([
        "docker", "inspect", "--format", "{{.State.Status}}", container_name
    ])

    if not success:
        return {"status": "not_found", "container": container_name, "ever_started": False}

    status = output.strip()
    result = {"status": status, "container": container_name}

    # Check if container has ever been started (StartedAt != 0001-01-01)
    success, started_at_str = await run_docker_command([
        "docker", "inspect", "--format", "{{.State.StartedAt}}", container_name
    ])
    ever_started = False
    if success and started_at_str.strip() and not started_at_str.startswith("0001-01-01"):
        ever_started = True
    result["ever_started"] = ever_started

    # If starting/restarting, check if it's loading
    if status == "running":
        # Check if container just started (less than 60 seconds ago)
        if success and started_at_str:
            try:
                started_at = datetime.fromisoformat(started_at_str.strip().replace('Z', '+00:00'))
                uptime_seconds = (datetime.now(started_at.tzinfo) - started_at).total_seconds()
                if uptime_seconds < 60:
                    result["status"] = "loading"
                # If running for > 90 seconds but health check still failing, check for errors
                elif uptime_seconds > 90:
                    # Get health status
                    health_success, health_status = await run_docker_command([
                        "docker", "inspect", "--format", "{{.State.Health.Status}}", container_name
                    ])
                    if health_success and health_status.strip() == "starting":
                        # Still in starting state after 90s - check logs for errors
                        log_success, logs = await run_docker_command([
                            "docker", "logs", "--tail", "100", container_name
                        ])
                        if log_success:
                            if "Engine core initialization failed" in logs or "RuntimeError" in logs:
                                # Check if it's a GPU memory issue
                                if "CUDA" in logs or "GPU" in logs or "memory" in logs.lower():
                                    result["status"] = "insufficient_gpu_ram"
                                    result["error"] = "Insufficient GPU memory - container stuck in starting state"
                                else:
                                    result["status"] = "failed"
                                    result["error"] = "Engine initialization failed - see container logs"
            except:
                pass

    # Check for exited/stopped state
    if status == "exited":
        # Check exit code for failure
        success, exit_code = await run_docker_command([
            "docker", "inspect", "--format", "{{.State.ExitCode}}", container_name
        ])
        if success and exit_code.strip() != "0":
            # Check logs for GPU memory error
            log_success, logs = await run_docker_command([
                "docker", "logs", "--tail", "100", container_name
            ])
            if log_success:
                # Check for explicit GPU memory errors
                if ("Free memory" in logs or "GPU memory utilization" in logs or "gpu_memory_utilization" in logs or
                    "OutOfMemory" in logs or "CUDA out of memory" in logs):
                    result["status"] = "insufficient_gpu_ram"
                    result["error"] = "Insufficient GPU memory available"
                # Check for Engine initialization failures (often GPU memory related)
                elif "Engine core initialization failed" in logs and "RuntimeError" in logs:
                    # This is likely a GPU memory issue - check if there's enough free memory
                    gpu_info = await get_gpu_memory_info()
                    model_metadata = MODEL_METADATA.get(
                        next((k for k, v in CONTAINER_NAMES.items() if v == container_name), None),
                        {}
                    )
                    required_gb = model_metadata.get("gpu_memory_gb", 0)
                    if required_gb > gpu_info.get("available_gb", 0) + 5:  # +5GB buffer for overhead
                        result["status"] = "insufficient_gpu_ram"
                        result["error"] = f"Engine initialization failed - likely insufficient GPU memory (need {required_gb}GB, have {gpu_info.get('available_gb', 0):.1f}GB available)"
                    else:
                        result["status"] = "failed"
                        result["error"] = "Engine initialization failed - see container logs"
                else:
                    result["status"] = "failed"
            else:
                result["status"] = "failed"
            result["exit_code"] = exit_code.strip()

    return result


@app.get("/v1/models/status")
async def get_models_status(api_key: str = Depends(verify_api_key)):
    """Get status of all model backends with download info and GPU memory"""
    statuses = {}

    # Get GPU memory info
    gpu_info = await get_gpu_memory_info()

    for model_name, container_name in CONTAINER_NAMES.items():
        container_status = await get_container_status(container_name)

        # Add model metadata
        metadata = MODEL_METADATA.get(model_name, {})
        container_status["size_gb"] = metadata.get("disk_size_gb")  # For display purposes
        container_status["gpu_memory_gb"] = metadata.get("gpu_memory_gb")  # Actual GPU memory requirement
        container_status["description"] = metadata.get("description")
        container_status["estimated_load_time_seconds"] = metadata.get("load_time_seconds", 60)

        # If running, show actual GPU memory usage
        # Note: We don't show live progress during loading because nvidia-smi reports
        # total GPU memory, not per-container memory, which gives misleading values
        if container_status["status"] == "running":
            # Get current GPU memory used by this container
            current_gpu_memory = await get_container_gpu_memory(container_name)
            container_status["gpu_memory_used_gb"] = current_gpu_memory

        # Check if model is downloaded
        # Logic:
        # 1. If container is running or loading → model MUST be downloaded
        # 2. If container has EVER started → model MUST be downloaded (can't run without files)
        # 3. Get model size info if available
        hf_path = metadata.get("hf_path")
        if hf_path:
            download_info = await check_model_downloaded(hf_path)
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

    # Add proactive GPU memory warnings for stopped models
    for model_name, status in statuses.items():
        # Only check stopped/exited/failed models that aren't currently running
        if status["status"] in ["exited", "not_found", "insufficient_gpu_ram"]:
            required_gb = status.get("gpu_memory_gb", 0)
            total_gpu = gpu_info.get("total_gb", 0)
            available_gpu = gpu_info.get("available_gb", 0)

            # Check if model is too big to ever fit (even with all models unloaded)
            if required_gb > total_gpu:
                status["status"] = "insufficient_gpu_ram"
                status["error"] = f"Model requires {required_gb}GB but GPU only has {total_gpu}GB total"
            # Check if model won't fit with current running models but could fit if we unload
            elif required_gb > available_gpu:
                status["status"] = "requires_unload"
                status["warning"] = "Starting will unload other models to free GPU memory"
                # Clear old error message
                if "error" in status:
                    del status["error"]
            # Model would fit with current available memory - clear any old error status
            else:
                if status["status"] == "insufficient_gpu_ram":
                    status["status"] = "exited"
                # Clear old error/warning messages
                if "error" in status:
                    del status["error"]
                if "warning" in status:
                    del status["warning"]

    return {
        "models": statuses,
        "gpu": gpu_info  # NEW: Add GPU memory info
    }


@app.post("/v1/models/{model_name}/start")
async def start_model(model_name: str, api_key: str = Depends(verify_api_key)):
    """Start a model backend container"""
    if model_name not in CONTAINER_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found. Available: {list(CONTAINER_NAMES.keys())}"
        )

    container_name = CONTAINER_NAMES[model_name]

    # Check if model is fully downloaded
    metadata = MODEL_METADATA.get(model_name, {})
    hf_path = metadata.get("hf_path")
    if hf_path:
        download_info = await check_model_downloaded(hf_path)
        if download_info["downloading"]:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' is still downloading. Please wait for download to complete. Current size: {download_info['size'] or 'unknown'}"
            )
        if not download_info["downloaded"]:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' is not fully downloaded. Please ensure the model files are downloaded before starting."
            )

    # Check current status
    status = await get_container_status(container_name)
    if status["status"] == "running":
        return {"message": f"Model '{model_name}' is already running", "status": "running"}

    # Get profile for this container (if any)
    profile = CONTAINER_PROFILES.get(container_name)
    # Use project directory as working directory so relative paths in docker-compose.yml work
    project_dir = os.path.dirname(DOCKER_COMPOSE_FILE)
    compose_cmd_base = ["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "-p", "local-llm-service"]
    if profile:
        compose_cmd_base.extend(["--profile", profile])

    # Set PWD to host project directory so ${PWD} in docker-compose.yml resolves correctly
    compose_env = {"PWD": HOST_PROJECT_DIR}

    # If container is in failed state, remove it and recreate using docker-compose
    if status["status"] in ["failed", "insufficient_gpu_ram"]:
        logger.info(f"Removing failed container '{container_name}' to clear error state")
        await run_docker_command(["docker", "rm", "-f", container_name])
        # Use docker-compose to recreate and start
        logger.info(f"Starting model '{model_name}' (container: {container_name})")
        success, output = await run_docker_command(compose_cmd_base + ["up", "-d", container_name], cwd=project_dir, env=compose_env)
    elif status["status"] == "exited":
        # Just restart if it was cleanly stopped
        logger.info(f"Starting model '{model_name}' (container: {container_name})")
        success, output = await run_docker_command(["docker", "start", container_name])
    else:
        # Container doesn't exist, use docker-compose to create and start
        logger.info(f"Starting model '{model_name}' (container: {container_name})")
        success, output = await run_docker_command(compose_cmd_base + ["up", "-d", container_name], cwd=project_dir, env=compose_env)

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


@app.post("/v1/models/switch")
async def switch_model(
    target_model: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Smart model switching with automatic memory management.

    Query Parameters:
        target_model: Name of the model to switch to

    Returns:
        Success: Information about the switch including unloaded models
        Error: Details about why the switch failed
    """

    # Validate model exists
    if target_model not in CONTAINER_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{target_model}' not found. Available: {list(CONTAINER_NAMES.keys())}"
        )

    # Step 1: Check if already running
    container_name = CONTAINER_NAMES[target_model]
    status = await get_container_status(container_name)

    if status["status"] == "running":
        # Check if healthy
        backend_url = MODEL_ROUTING.get(target_model)
        if backend_url:
            health = await check_backend_health(backend_url)
            if health.get("status") == "healthy":
                return {
                    "status": "already_loaded",
                    "model": target_model,
                    "message": f"Model '{target_model}' is already running and healthy"
                }

    # Step 2: Get memory requirements
    metadata = MODEL_METADATA.get(target_model, {})
    required_memory_gb = metadata.get("gpu_memory_gb", 0)  # Actual GPU memory needed

    # Step 3: Check available memory
    gpu_info = await get_gpu_memory_info()
    available_gb = gpu_info["available_gb"]

    logger.info(
        f"Model switch requested: {target_model} | "
        f"Required: {required_memory_gb:.1f}GB | Available: {available_gb:.1f}GB"
    )

    # Step 4: Unload models if needed (largest first strategy)
    unloaded_models = []
    if available_gb < required_memory_gb:
        # Get all running models
        all_statuses = await get_models_status(api_key)
        running_models = []

        for model_name, model_status in all_statuses["models"].items():
            if model_name != target_model and model_status["status"] == "running":
                model_metadata = MODEL_METADATA.get(model_name, {})
                gpu_memory_gb = model_metadata.get("gpu_memory_gb", 0)
                running_models.append({
                    "name": model_name,
                    "gpu_memory_gb": gpu_memory_gb
                })

        # Sort by GPU memory (largest first) for efficient unloading
        running_models.sort(key=lambda m: m["gpu_memory_gb"], reverse=True)

        # Unload models until we have enough memory
        freed_memory = 0
        for model in running_models:
            if available_gb + freed_memory >= required_memory_gb:
                break

            # Stop this model
            logger.info(f"Unloading {model['name']} ({model['gpu_memory_gb']}GB GPU) to free memory")
            await stop_model(model["name"], api_key)
            unloaded_models.append(model["name"])
            freed_memory += model["gpu_memory_gb"]

            # Wait for container to stop and GPU memory to be fully released
            # Increased to 15 seconds to avoid memory profiling errors during model switch
            logger.info("Waiting for GPU memory to be released...")
            await asyncio.sleep(15)

        # Refresh GPU memory info after stopping models
        gpu_info_after = await get_gpu_memory_info()
        total_available = gpu_info_after["available_gb"]

        logger.info(f"After unloading: Available GPU memory: {total_available:.1f}GB")

        if total_available < required_memory_gb:
            return {
                "status": "error",
                "error": "insufficient_memory",
                "message": (
                    f"Cannot free enough GPU memory to load {target_model}. "
                    f"Required: {required_memory_gb:.1f}GB, "
                    f"Available after unloading all models: {total_available:.1f}GB"
                ),
                "required_gb": round(required_memory_gb, 1),
                "available_gb": round(available_gb, 1),
                "freed_gb": round(freed_memory, 1),
                "total_available_gb": round(total_available, 1)
            }

    # Step 5: Start target model
    logger.info(f"Starting {target_model}...")
    start_result = await start_model(target_model, api_key)

    return {
        "status": "success",
        "model": target_model,
        "unloaded_models": unloaded_models,
        "start_result": start_result,
        "estimated_load_time_seconds": metadata.get("load_time_seconds", 60),
        "memory_info": {
            "required_gb": round(required_memory_gb, 1),
            "available_before_gb": round(available_gb, 1),
            "freed_gb": round(sum([m["gpu_memory_gb"] for m in running_models if m["name"] in unloaded_models]), 1) if unloaded_models else 0
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
