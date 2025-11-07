#!/bin/bash

# Test script to verify detection of containers stuck in loading state
# This simulates the scenario where a model fails to load due to insufficient GPU RAM

set -e

API_KEY="${API_KEY:-sk-local-2ac9387d659f7131f38d83e5f7bee469}"
API_URL="http://localhost:8080/v1"

echo "========================================="
echo "Test: Stuck Loading Detection"
echo "========================================="
echo ""

# Check current GPU memory
echo "1. Checking current GPU memory..."
GPU_INFO=$(curl -s -H "Authorization: Bearer $API_KEY" "$API_URL/models/status" | python3 -c "import sys, json; data=json.load(sys.stdin); gpu=data['gpu']; print(f\"{gpu['used_gb']}GB / {gpu['total_gb']}GB (Available: {gpu['available_gb']}GB)\")")
echo "   GPU Memory: $GPU_INFO"
echo ""

# Check which models are currently running
echo "2. Checking running models..."
RUNNING_MODELS=$(curl -s -H "Authorization: Bearer $API_KEY" "$API_URL/models/status" | python3 -c "import sys, json; data=json.load(sys.stdin); running=[name for name, m in data['models'].items() if m['status']=='running']; print(', '.join(running) if running else 'None')")
echo "   Running: $RUNNING_MODELS"
echo ""

# Start a model that will fail due to insufficient GPU RAM
# We'll start deepseek-coder while gpt-oss-120b is running (not enough memory for both)
echo "3. Starting deepseek-coder-33b-instruct (should fail - insufficient GPU RAM)..."
START_RESULT=$(curl -s -X POST -H "Authorization: Bearer $API_KEY" "$API_URL/models/deepseek-coder-33b-instruct/start" | python3 -c "import sys, json; r=json.load(sys.stdin); print(r.get('message', 'Unknown'))")
echo "   Start result: $START_RESULT"
echo ""

# Wait and check status every 30 seconds
echo "4. Monitoring status (checking every 30s for up to 120s)..."
for i in {1..4}; do
    ELAPSED=$((i * 30))
    echo "   After ${ELAPSED}s:"

    STATUS_INFO=$(curl -s -H "Authorization: Bearer $API_KEY" "$API_URL/models/status" | python3 -c "
import sys, json
data = json.load(sys.stdin)
m = data['models']['deepseek-coder-33b-instruct']
print(f\"     Status: {m['status']}\")
print(f\"     Health: {m.get('health', 'N/A')}\")
if 'error' in m:
    print(f\"     Error: {m['error']}\")
")
    echo "$STATUS_INFO"

    # Check if status changed to insufficient_gpu_ram or failed
    CURRENT_STATUS=$(curl -s -H "Authorization: Bearer $API_KEY" "$API_URL/models/status" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['models']['deepseek-coder-33b-instruct']['status'])")

    if [ "$CURRENT_STATUS" = "insufficient_gpu_ram" ]; then
        echo ""
        echo "✅ TEST PASSED: Status correctly detected as 'insufficient_gpu_ram'"
        echo ""

        # Clean up - stop the container
        echo "5. Cleaning up..."
        docker stop vllm-coder 2>/dev/null || true
        echo "   Stopped vllm-coder"
        exit 0
    elif [ "$CURRENT_STATUS" = "failed" ]; then
        echo ""
        echo "⚠️  TEST WARNING: Status detected as 'failed' (expected 'insufficient_gpu_ram')"
        echo ""

        # Clean up
        echo "5. Cleaning up..."
        docker stop vllm-coder 2>/dev/null || true
        echo "   Stopped vllm-coder"
        exit 1
    elif [ "$CURRENT_STATUS" != "loading" ] && [ "$CURRENT_STATUS" != "running" ]; then
        echo ""
        echo "❌ TEST FAILED: Unexpected status '$CURRENT_STATUS'"
        echo ""

        # Clean up
        echo "5. Cleaning up..."
        docker stop vllm-coder 2>/dev/null || true
        echo "   Stopped vllm-coder"
        exit 1
    fi

    # Wait before next check (except on last iteration)
    if [ $i -lt 4 ]; then
        sleep 30
    fi
done

echo ""
echo "⏱️  TEST TIMEOUT: Status still 'loading' after 120s"
echo "   (Detection threshold is 90s, may need a bit more time)"
echo ""

# Clean up
echo "5. Cleaning up..."
docker stop vllm-coder 2>/dev/null || true
echo "   Stopped vllm-coder"

exit 1
