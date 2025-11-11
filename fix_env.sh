#!/bin/bash
set -e

#==============================================================================
# Fix Missing .env File
#==============================================================================
# This script creates the .env file in /opt/local_llm_service
#
# Usage:
#   sudo ./fix_env.sh
#==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/local_llm_service"
SERVICE_NAME="local-llm-service"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

print_info "Creating .env file in $INSTALL_DIR..."

# Check if .env already exists
if [[ -f "$INSTALL_DIR/.env" ]]; then
    print_info ".env file already exists"
    read -p "Overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Keeping existing .env file"
        exit 0
    fi
fi

# Copy from template
if [[ ! -f "$INSTALL_DIR/.env.example" ]]; then
    print_error ".env.example not found in $INSTALL_DIR"
    exit 1
fi

cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"

# Generate a random API key
RANDOM_API_KEY="sk-local-$(openssl rand -hex 16)"
sed -i "s/sk-local-your-secret-key-here/$RANDOM_API_KEY/" "$INSTALL_DIR/.env"

print_success ".env file created with API key: $RANDOM_API_KEY"
print_info "Restarting containers to apply changes..."

# Stop and remove old containers to avoid conflicts
cd "$INSTALL_DIR"
docker compose down 2>/dev/null || true
docker rm -f vllm-router webui-frontend 2>/dev/null || true

# Start containers
docker compose up -d

# Wait for containers to start
sleep 8

# Check status
if docker ps --filter "name=vllm-router" --filter "status=running" | grep -q vllm-router; then
    print_success "Containers started successfully"
    echo ""
    echo "Access the WebUI at: http://localhost:3000"
    echo ""
    echo "The models should now be visible in the Model Manager."
    echo "API Key: $RANDOM_API_KEY"
else
    print_error "Containers failed to start"
    echo "Check logs with: docker logs vllm-router"
    exit 1
fi

print_success "Fix applied successfully!"
