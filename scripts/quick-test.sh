#!/bin/bash
# Quick test script - basic health checks before full validation

set -e

ROUTER_URL="${ROUTER_URL:-http://localhost:8080}"

echo "Quick Service Test"
echo "=================="
echo ""

# Check if Docker Compose is running
echo -n "Checking Docker containers... "
if docker compose ps | grep -q "Up"; then
    echo "✓ Running"
else
    echo "✗ Not running"
    echo "Start services with: docker compose up -d"
    exit 1
fi

# Check router health
echo -n "Checking router health... "
if curl -sf "$ROUTER_URL/health" > /dev/null 2>&1; then
    echo "✓ Healthy"
else
    echo "✗ Unhealthy"
    echo "Check logs with: docker compose logs vllm-router"
    exit 1
fi

# Check model readiness
echo -n "Checking model readiness... "
ready_response=$(curl -s "$ROUTER_URL/ready")
if echo "$ready_response" | grep -q '"status":"ready"'; then
    echo "✓ Ready"
    echo ""
    echo "Available models:"
    echo "$ready_response" | grep -o '"[^"]*":\s*"[^"]*"' | sed 's/^/  /'
else
    echo "⏳ Models still loading"
    echo "Check status with: docker compose logs -f vllm-coder vllm-general"
fi

echo ""
echo "Service is operational!"
echo "Run full validation: ./scripts/validate-deployment.sh"
