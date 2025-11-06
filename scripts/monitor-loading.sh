#!/bin/bash
# Monitor model loading progress

echo "=========================================="
echo "Model Loading Monitor"
echo "=========================================="
echo ""
echo "This will monitor until both models are ready (5-10 minutes)"
echo "Press Ctrl+C to exit monitoring"
echo ""

API_KEY=$(grep "^API_KEY=" .env | cut -d= -f2)

while true; do
    clear
    echo "=========================================="
    echo "Model Loading Status - $(date +%H:%M:%S)"
    echo "=========================================="
    echo ""

    # Check readiness
    READY_RESPONSE=$(curl -s http://localhost:8080/ready)
    echo "$READY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$READY_RESPONSE"

    echo ""
    echo "Container Status:"
    docker compose ps | grep -E "NAME|vllm"

    echo ""
    echo "Recent Logs (Coder Model):"
    docker compose logs --tail=3 vllm-coder 2>&1 | grep -E "(INFO|Loading|model)" | tail -3

    echo ""
    echo "Recent Logs (General Model):"
    docker compose logs --tail=3 vllm-general 2>&1 | grep -E "(INFO|Loading|model)" | tail -3

    # Check if ready
    if echo "$READY_RESPONSE" | grep -q '"status":"ready"'; then
        echo ""
        echo "=========================================="
        echo "✓ SUCCESS! Both models are ready!"
        echo "=========================================="
        echo ""
        echo "You can now:"
        echo "  1. Test the API: curl http://localhost:8080/v1/models -H \"Authorization: Bearer $API_KEY\""
        echo "  2. Run validation: ./scripts/validate-deployment.sh"
        echo "  3. Configure your IDE: see docs/ide-integration.md"
        break
    fi

    sleep 10
done
