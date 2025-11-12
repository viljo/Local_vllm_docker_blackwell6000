#!/bin/bash

# View Logs Helper Script
# Makes it easy to view and filter router logs

show_help() {
    cat << EOF
Usage: ./scripts/view-logs.sh [OPTIONS]

View and filter vLLM router logs

OPTIONS:
    errors              Show only ERROR level logs
    warnings            Show only WARNING level logs
    chat                Show only chat completion requests
    tools               Show only tool-related logs
    auth                Show authentication failures
    backend             Show backend communication logs
    request [ID]        Show logs for specific request ID
    tail                Follow logs in real-time
    last [N]            Show last N lines (default: 50)
    since [TIME]        Show logs since time (e.g., "5m", "1h", "2025-11-12")

    --no-color          Disable colored output
    -h, --help          Show this help

EXAMPLES:
    ./scripts/view-logs.sh errors              # Show all errors
    ./scripts/view-logs.sh last 100            # Show last 100 lines
    ./scripts/view-logs.sh since 10m           # Show logs from last 10 minutes
    ./scripts/view-logs.sh request abc123      # Show logs for request ID abc123
    ./scripts/view-logs.sh tail                # Follow logs in real-time
    ./scripts/view-logs.sh chat | grep tool    # Show chat requests with tools

EOF
}

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
USE_COLOR=true

# Check for --no-color flag
for arg in "$@"; do
    if [ "$arg" = "--no-color" ]; then
        USE_COLOR=false
        break
    fi
done

colorize() {
    if [ "$USE_COLOR" = true ]; then
        sed -E \
            -e "s/(ERROR[^:]*)/$(echo -e "${RED}")\1$(echo -e "${NC}")/g" \
            -e "s/(WARNING[^:]*)/$(echo -e "${YELLOW}")\1$(echo -e "${NC}")/g" \
            -e "s/(INFO[^:]*)/$(echo -e "${GREEN}")\1$(echo -e "${NC}")/g" \
            -e "s/(HTTP Request|Backend)/$(echo -e "${BLUE}")\1$(echo -e "${NC}")/g"
    else
        cat
    fi
}

case "$1" in
    errors)
        echo "=== ERROR Level Logs ==="
        docker logs vllm-router 2>&1 | grep -E "ERROR|Exception|Traceback" | colorize
        ;;

    warnings)
        echo "=== WARNING Level Logs ==="
        docker logs vllm-router 2>&1 | grep "WARNING" | colorize
        ;;

    chat)
        echo "=== Chat Completion Requests ==="
        docker logs vllm-router 2>&1 | grep "Chat completion request" | colorize
        ;;

    tools)
        echo "=== Tool-Related Logs ==="
        docker logs vllm-router 2>&1 | grep -iE "tool|function" | colorize
        ;;

    auth)
        echo "=== Authentication Failures ==="
        docker logs vllm-router 2>&1 | grep -i "invalid.*key\|401\|unauthorized" | colorize
        ;;

    backend)
        echo "=== Backend Communication ==="
        docker logs vllm-router 2>&1 | grep -E "Backend|HTTP Request|Routing to" | colorize
        ;;

    request)
        if [ -z "$2" ]; then
            echo "Error: Please provide a request ID"
            echo "Usage: $0 request <REQUEST_ID>"
            exit 1
        fi
        echo "=== Logs for Request: $2 ==="
        docker logs vllm-router 2>&1 | grep "$2" | colorize
        ;;

    tail)
        echo "=== Following logs (Ctrl+C to stop) ==="
        docker logs vllm-router -f 2>&1 | colorize
        ;;

    last)
        LINES=${2:-50}
        echo "=== Last $LINES log lines ==="
        docker logs vllm-router --tail "$LINES" 2>&1 | colorize
        ;;

    since)
        if [ -z "$2" ]; then
            echo "Error: Please provide a time period"
            echo "Usage: $0 since <TIME> (e.g., '5m', '1h', '2025-11-12')"
            exit 1
        fi
        echo "=== Logs since $2 ==="
        docker logs vllm-router --since "$2" 2>&1 | colorize
        ;;

    -h|--help|help)
        show_help
        ;;

    "")
        # Default: show last 50 lines
        echo "=== Last 50 log lines (use --help for more options) ==="
        docker logs vllm-router --tail 50 2>&1 | colorize
        ;;

    *)
        echo "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
