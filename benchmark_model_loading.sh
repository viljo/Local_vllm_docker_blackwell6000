#!/bin/bash
# Benchmark model loading time for vLLM containers

MODEL_NAME=${1:-"gpt-oss-120b"}
CONTAINER_NAME="vllm-${MODEL_NAME}"

echo "======================================================================"
echo "MODEL LOADING BENCHMARK"
echo "======================================================================"
echo "Model: $MODEL_NAME"
echo "Container: $CONTAINER_NAME"
echo ""

# Check if container is running
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo "⚠ Container is already running. Stopping it first..."
    docker stop "$CONTAINER_NAME"
    sleep 3
fi

echo "Starting model loading benchmark..."
echo ""

# Record start time
START_TIME=$(date +%s)
echo "Start time: $(date)"
echo ""

# Start the container
echo "Starting container: $CONTAINER_NAME"
docker compose up -d "$CONTAINER_NAME"

echo ""
echo "Waiting for model to load into GPU memory..."
echo "(Monitoring /health endpoint until ready)"
echo ""

# Monitor health endpoint
ELAPSED=0
READY=false

while [ $ELAPSED -lt 1800 ]; do  # Max 30 minutes
    sleep 5
    ELAPSED=$(($(date +%s) - START_TIME))

    # Try to curl the health endpoint
    if docker exec "$CONTAINER_NAME" curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        READY=true
        break
    fi

    # Show progress every 30 seconds
    if [ $((ELAPSED % 30)) -eq 0 ]; then
        MINUTES=$((ELAPSED / 60))
        SECONDS=$((ELAPSED % 60))
        echo "  ${MINUTES}m ${SECONDS}s - Still loading..."

        # Check GPU memory usage
        GPU_MEM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
        echo "  GPU memory used: ${GPU_MEM} MiB"
    fi
done

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo ""
echo "======================================================================"
if [ "$READY" = true ]; then
    MINUTES=$((TOTAL_TIME / 60))
    SECONDS=$((TOTAL_TIME % 60))

    echo "✓ Model loaded successfully!"
    echo ""
    echo "Total loading time: ${MINUTES}m ${SECONDS}s (${TOTAL_TIME} seconds)"
    echo "End time: $(date)"
    echo ""

    # Get final GPU stats
    echo "Final GPU stats:"
    nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader

    echo ""
    echo "Model is ready at:"
    if [ "$MODEL_NAME" = "gpt-oss-120b" ]; then
        echo "  http://localhost:8002/v1/models"
    elif [ "$MODEL_NAME" = "gpt-oss-20b" ]; then
        echo "  http://localhost:8003/v1/models"
    fi

    exit 0
else
    echo "✗ Model failed to load within 30 minutes"
    echo ""
    echo "Container logs:"
    docker logs "$CONTAINER_NAME" --tail 50
    exit 1
fi
