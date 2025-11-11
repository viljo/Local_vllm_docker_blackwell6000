#!/bin/bash
# Local LLM Service - Master Run Script
# Handles setup, launch, and validation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Local LLM Service - Launch Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}===> $1${NC}"
    echo ""
}

# Check prerequisites
print_section "Checking Prerequisites"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found: $(docker --version)${NC}"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found. Please install Docker Compose v2.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found: $(docker compose version)${NC}"

# Check NVIDIA driver
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}⚠ nvidia-smi not found. GPU support may not work.${NC}"
else
    echo -e "${GREEN}✓ NVIDIA driver found${NC}"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1
fi

# Check .env file
print_section "Checking Configuration"

# Function to generate secure API key
generate_api_key() {
    if command -v python3 &> /dev/null; then
        # Preferred: Use Python's secrets module (cryptographically secure)
        python3 -c "import secrets; print('sk-local-' + secrets.token_hex(32))"
    elif command -v openssl &> /dev/null; then
        # Fallback: Use openssl (but only 32 hex chars = 128 bits)
        echo "sk-local-$(openssl rand -hex 32)"
    else
        echo -e "${RED}✗ Cannot generate API key: neither python3 nor openssl found${NC}"
        exit 1
    fi
}

# List of known weak/compromised API keys
WEAK_KEYS=(
    "sk-local-dev-key"
    "sk-local-your-secret-key-here"
    "sk-local-CHANGE-THIS-TO-A-SECURE-RANDOM-KEY"
    "sk-local-2ac9387d659f7131f38d83e5f7bee469"  # Compromised key from old code
)

# Check if API key is weak
is_weak_api_key() {
    local key=$1
    for weak_key in "${WEAK_KEYS[@]}"; do
        if [ "$key" = "$weak_key" ]; then
            return 0  # true - it is weak
        fi
    done
    # Also check if key is too short (less than 32 characters after prefix)
    local key_without_prefix=${key#sk-local-}
    if [ ${#key_without_prefix} -lt 32 ]; then
        return 0  # true - it is weak
    fi
    return 1  # false - not weak
}

if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found. Creating from template...${NC}"

    if [ -f .env.example ]; then
        cp .env.example .env

        # Generate API key
        echo "Generating secure API key..."
        API_KEY=$(generate_api_key)

        # Update .env with generated key
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/API_KEY=.*/API_KEY=${API_KEY}/" .env
        else
            sed -i "s/API_KEY=.*/API_KEY=${API_KEY}/" .env
        fi

        echo -e "${GREEN}✓ Created .env file with generated API key${NC}"
        echo -e "${YELLOW}  API Key: ${API_KEY}${NC}"
        echo -e "${YELLOW}  Saved to .env file${NC}"
    else
        echo -e "${RED}✗ .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"

    # Extract API key from .env
    API_KEY=$(grep "^API_KEY=" .env 2>/dev/null | cut -d= -f2)

    if [ -z "$API_KEY" ]; then
        echo -e "${RED}✗ No API_KEY found in .env file${NC}"
        echo "Generating new API key..."
        API_KEY=$(generate_api_key)
        echo "API_KEY=${API_KEY}" >> .env
        echo -e "${GREEN}✓ Generated and saved new API key${NC}"
        echo -e "${YELLOW}  API Key: ${API_KEY}${NC}"
    elif is_weak_api_key "$API_KEY"; then
        echo -e "${RED}⚠ WARNING: Weak or compromised API key detected!${NC}"
        echo -e "${YELLOW}  Current key: ${API_KEY}${NC}"
        echo ""
        echo "This key is either:"
        echo "  • A default/example key from .env.example"
        echo "  • A previously compromised key"
        echo "  • Too short to be secure"
        echo ""
        echo -n "Generate a new secure API key? [Y/n]: "
        read -r response

        # Default to yes if empty response
        response=${response:-y}

        if [[ "$response" =~ ^[Yy]$ ]] || [ -z "$response" ]; then
            # Generate new key
            NEW_API_KEY=$(generate_api_key)

            # Update .env file
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/API_KEY=.*/API_KEY=${NEW_API_KEY}/" .env
            else
                sed -i "s/API_KEY=.*/API_KEY=${NEW_API_KEY}/" .env
            fi

            echo -e "${GREEN}✓ Generated new secure API key${NC}"
            echo -e "${YELLOW}  New API Key: ${NEW_API_KEY}${NC}"
            echo -e "${YELLOW}  Updated in .env file${NC}"
            API_KEY="$NEW_API_KEY"
        else
            echo -e "${YELLOW}⚠ Keeping existing API key (not recommended)${NC}"
        fi
    else
        echo -e "${GREEN}✓ API key looks secure${NC}"
        # Only show first/last 8 chars for security
        echo -e "  API Key: ${API_KEY:0:10}...${API_KEY: -8}"
    fi
fi

echo ""

# Parse command line arguments
ACTION="${1:-start}"

case "$ACTION" in
    start|up)
        print_section "Starting Services"

        echo "Pulling latest images..."
        docker compose pull

        echo ""
        echo "Starting containers..."
        docker compose up -d

        echo ""
        echo -e "${GREEN}✓ Services started${NC}"
        echo ""
        echo "Container status:"
        docker compose ps

        print_section "Waiting for Services to Initialize"

        echo "This may take 5-10 minutes for models to load..."
        echo "You can monitor progress with: docker compose logs -f"
        echo ""

        # Wait for router to be healthy
        echo -n "Waiting for router to start..."
        for i in {1..30}; do
            if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
                echo -e " ${GREEN}✓${NC}"
                break
            fi
            echo -n "."
            sleep 2
        done

        # Check if models are ready (non-blocking)
        echo -n "Checking model status..."
        if curl -sf http://localhost:8080/ready > /dev/null 2>&1; then
            echo -e " ${GREEN}✓ Models ready${NC}"

            # Run quick test
            echo ""
            if [ -x ./scripts/quick-test.sh ]; then
                ./scripts/quick-test.sh
            fi

            print_section "Service Ready!"
            echo -e "${GREEN}✓ All services are operational${NC}"
            echo ""
            echo "Access points:"
            echo "  • API Endpoint: http://localhost:8080"
            echo "  • Health Check: http://localhost:8080/health"
            echo "  • Model List:   http://localhost:8080/v1/models"
            echo ""
            echo "Next steps:"
            echo "  1. Configure your IDE (see docs/ide-integration.md)"
            echo "  2. Run validation: ./scripts/validate-deployment.sh"
            echo "  3. Test API: ./scripts/quick-test.sh"
            echo ""
            echo "Useful commands:"
            echo "  • View logs:    docker compose logs -f"
            echo "  • Stop service: docker compose stop"
            echo "  • Full reset:   docker compose down -v"

        else
            echo -e " ${YELLOW}⏳ Models still loading${NC}"
            echo ""
            echo "Models are loading in the background (this takes 5-10 minutes)."
            echo "Monitor progress with:"
            echo ""
            echo "  docker compose logs -f vllm-coder"
            echo "  docker compose logs -f vllm-general"
            echo ""
            echo "Check readiness with:"
            echo "  curl http://localhost:8080/ready"
        fi
        ;;

    stop)
        print_section "Stopping Services"
        docker compose stop
        echo -e "${GREEN}✓ Services stopped${NC}"
        echo "Containers are stopped but not removed."
        echo "Start again with: ./run.sh start"
        ;;

    restart)
        print_section "Restarting Services"
        docker compose restart
        echo -e "${GREEN}✓ Services restarted${NC}"
        ;;

    down)
        print_section "Removing Services"
        echo -e "${YELLOW}This will stop and remove all containers.${NC}"
        echo -e "${YELLOW}Model weights and data will be preserved.${NC}"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down
            echo -e "${GREEN}✓ Services removed${NC}"
        else
            echo "Cancelled."
        fi
        ;;

    logs)
        SERVICE="${2:-}"
        if [ -z "$SERVICE" ]; then
            docker compose logs -f
        else
            docker compose logs -f "$SERVICE"
        fi
        ;;

    status|ps)
        print_section "Service Status"
        docker compose ps
        echo ""

        # Check API health
        if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
            echo -e "Router: ${GREEN}✓ Healthy${NC}"

            if curl -sf http://localhost:8080/ready > /dev/null 2>&1; then
                echo -e "Models: ${GREEN}✓ Ready${NC}"
            else
                echo -e "Models: ${YELLOW}⏳ Loading${NC}"
            fi
        else
            echo -e "Router: ${RED}✗ Unhealthy${NC}"
        fi
        ;;

    test|validate)
        print_section "Running Validation Tests"
        if [ -x ./scripts/validate-deployment.sh ]; then
            ./scripts/validate-deployment.sh
        else
            echo -e "${RED}✗ Validation script not found or not executable${NC}"
            exit 1
        fi
        ;;

    clean)
        print_section "Deep Clean"
        echo -e "${RED}WARNING: This will remove all containers, volumes, and cached models!${NC}"
        echo -e "${RED}You will need to re-download models on next startup.${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v
            rm -rf models/* data/* config/*
            echo -e "${GREEN}✓ Clean complete${NC}"
        else
            echo "Cancelled."
        fi
        ;;

    help|--help|-h)
        echo "Local LLM Service - Run Script"
        echo ""
        echo "Usage: ./run.sh [command]"
        echo ""
        echo "Commands:"
        echo "  start, up      Start all services (default)"
        echo "  stop           Stop all services (keeps containers)"
        echo "  restart        Restart all services"
        echo "  down           Stop and remove containers"
        echo "  logs [service] View logs (all or specific service)"
        echo "  status, ps     Show service status"
        echo "  test, validate Run validation tests"
        echo "  clean          Remove everything including volumes"
        echo "  help           Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run.sh                    # Start services"
        echo "  ./run.sh logs vllm-coder   # View coder logs"
        echo "  ./run.sh test              # Run validation"
        echo "  ./run.sh stop              # Stop services"
        echo ""
        ;;

    *)
        echo -e "${RED}Unknown command: $ACTION${NC}"
        echo "Use './run.sh help' for usage information"
        exit 1
        ;;
esac
