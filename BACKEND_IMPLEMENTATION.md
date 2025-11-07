# Backend Implementation - Smart Model Switching

This document contains all the backend code changes needed. Apply these changes to `router/app/main.py`.

## Change 1: Add GPU Memory Utility Function

**Location:** After the `check_model_downloaded` function (around line 500)

**Add this new function:**

```python
async def get_gpu_memory_info() -> dict:
    """Get current GPU memory usage using nvidia-smi"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            used, total = result.stdout.strip().split(", ")
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
```

## Change 2: Update MODEL_METADATA with Load Times

**Location:** Line 424-450 (MODEL_METADATA definition)

**Replace the existing MODEL_METADATA with:**

```python
MODEL_METADATA = {
    "gpt-oss-120b": {
        "size_gb": 183,  # Updated from 80 to actual size
        "hf_path": "openai/gpt-oss-120b",
        "description": "GPT-OSS 120B - Advanced reasoning (117B params, 5.1B active)",
        "load_time_seconds": 61  # NEW: From benchmark
    },
    "gpt-oss-20b": {
        "size_gb": 40,
        "hf_path": "openai/gpt-oss-20b",
        "description": "GPT-OSS 20B - Efficient reasoning (21B params, 3.6B active)",
        "load_time_seconds": 15  # NEW: Estimated
    },
    "deepseek-coder-33b-instruct": {
        "size_gb": 43,
        "hf_path": "deepseek-ai/deepseek-coder-33b-instruct",
        "description": "DeepSeek Coder 33B - Python specialist",
        "load_time_seconds": 20  # NEW: Estimated
    },
    "mistral-7b-v0.1": {
        "size_gb": 7,
        "hf_path": "mistralai/Mistral-7B-v0.1",
        "description": "Mistral 7B - General purpose",
        "load_time_seconds": 8  # NEW: Estimated
    }
}
```

## Change 3: Enhance `/v1/models/status` Endpoint

**Location:** Line 568-604 (get_models_status function)

**Replace with:**

```python
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
        container_status["size_gb"] = metadata.get("size_gb")
        container_status["description"] = metadata.get("description")
        container_status["estimated_load_time_seconds"] = metadata.get("load_time_seconds", 60)

        # If running, estimate GPU memory usage (85% of model size for vLLM)
        if container_status["status"] == "running":
            model_size_gb = metadata.get("size_gb", 0)
            container_status["gpu_memory_used_gb"] = round(model_size_gb * 0.85, 1)

        # Check if model is downloaded
        hf_path = metadata.get("hf_path")
        if hf_path:
            download_info = await check_model_downloaded(hf_path)
            container_status["downloaded_size"] = download_info["size"]

        # Check backend health if running
        if container_status["status"] == "running":
            backend_url = MODEL_ROUTING.get(model_name)
            if backend_url:
                health = await check_backend_health(backend_url)
                container_status["health"] = health.get("status", "unknown")

                # If health check fails, might still be loading
                if container_status["health"] != "healthy":
                    container_status["status"] = "loading"

        statuses[model_name] = container_status

    return {
        "models": statuses,
        "gpu": gpu_info  # NEW: Add GPU memory info
    }
```

## Change 4: Add Smart Model Switching Endpoint

**Location:** After restart_model function (line ~698, before `if __name__ == "__main__"`)

**Add this new endpoint:**

```python
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
    model_size_gb = metadata.get("size_gb", 0)
    required_memory_gb = model_size_gb * 0.85  # 85% GPU memory utilization

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
                size_gb = model_metadata.get("size_gb", 0)
                running_models.append({
                    "name": model_name,
                    "size_gb": size_gb,
                    "memory_gb": size_gb * 0.85
                })

        # Sort by size (largest first) for efficient unloading
        running_models.sort(key=lambda m: m["size_gb"], reverse=True)

        # Unload models until we have enough memory
        freed_memory = 0
        for model in running_models:
            if available_gb + freed_memory >= required_memory_gb:
                break

            # Stop this model
            logger.info(f"Unloading {model['name']} ({model['size_gb']}GB) to free memory")
            await stop_model(model["name"], api_key)
            unloaded_models.append(model["name"])
            freed_memory += model["memory_gb"]

            # Brief pause to let container stop
            await asyncio.sleep(2)

        # Check if we have enough memory now
        total_available = available_gb + freed_memory
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
            "freed_gb": round(sum([m["memory_gb"] for m in running_models if m["name"] in unloaded_models]), 1) if unloaded_models else 0
        }
    }
```

---

## Testing the Changes

After applying these changes, restart the router:

```bash
# Rebuild and restart router
docker compose build vllm-router
docker compose up -d vllm-router
```

Then test:

```bash
# Test 1: Enhanced status endpoint
curl -H "Authorization: Bearer sk-local-2ac9387d659f7131f38d83e5f7bee469" \
  http://localhost:8080/v1/models/status | jq .

# Should show gpu: { used_gb, total_gb, available_gb }

# Test 2: Switch models
curl -X POST -H "Authorization: Bearer sk-local-2ac9387d659f7131f38d83e5f7bee469" \
  "http://localhost:8080/v1/models/switch?target_model=gpt-oss-120b" | jq .

# Should return success with unloaded_models list
```

---

## Summary of Changes

1. **Added `get_gpu_memory_info()`** - Utility function to query nvidia-smi
2. **Updated `MODEL_METADATA`** - Added `load_time_seconds` and corrected sizes
3. **Enhanced `/v1/models/status`** - Now returns GPU memory info
4. **Added `/v1/models/switch`** - Smart switching with auto-unload

These changes enable:
- Frontend to see ALL models (not just running)
- Frontend to know available GPU memory
- One-click model switching
- Automatic memory management (unload largest models first)
- Estimated load times for progress indicators

**Next:** Frontend implementation (will create separate file due to size)
