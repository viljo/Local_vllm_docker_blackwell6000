#!/bin/bash
set -e

#==============================================================================
# Migrate existing installation to use /ssd/LLMs
#==============================================================================
# This script migrates the current installation from ./models to /ssd/LLMs
#
# Usage:
#   sudo ./migrate_to_ssd.sh
#==============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/local_llm_service"
MODELS_DIR="/ssd/LLMs"
DEV_MODELS="/home/asvil/git/local_llm_service/models"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

echo ""
echo "========================================================================"
print_info "Migrating Local vLLM Service to use /ssd/LLMs"
echo "========================================================================"
echo ""

# Step 1: Create /ssd/LLMs directory
print_info "Creating $MODELS_DIR directory..."
mkdir -p "$MODELS_DIR"
chown -R root:root "$MODELS_DIR"
print_success "Directory created"

# Step 2: Check for models in dev directory
if [[ -d "$DEV_MODELS" ]]; then
    MODEL_COUNT=$(find "$DEV_MODELS" -type d -name "models--*" 2>/dev/null | wc -l)

    if [[ $MODEL_COUNT -gt 0 ]]; then
        print_info "Found $MODEL_COUNT model(s) in dev directory"
        print_info "Copying models to $MODELS_DIR..."
        print_warning "This may take several minutes for large models..."

        rsync -av --info=progress2 "$DEV_MODELS/" "$MODELS_DIR/"

        print_success "Models copied successfully"
    else
        print_info "No models found in dev directory"
    fi
else
    print_info "Dev models directory not found, skipping copy"
fi

# Step 3: Stop containers
print_info "Stopping containers..."
cd "$INSTALL_DIR"
docker compose down 2>/dev/null || true
docker rm -f vllm-router webui-frontend 2>/dev/null || true
print_success "Containers stopped"

# Step 4: Update docker-compose.yml
print_info "Updating docker-compose.yml..."
sed -i "s|./models:/models|$MODELS_DIR:/models|g" "$INSTALL_DIR/docker-compose.yml"
print_success "docker-compose.yml updated"

# Step 5: Start containers
print_info "Starting containers..."
docker compose up -d
print_success "Containers started"

# Wait for containers to start
sleep 8

# Check status
if docker ps --filter "name=vllm-router" --filter "status=running" | grep -q vllm-router; then
    echo ""
    echo "========================================================================"
    print_success "Migration complete!"
    echo "========================================================================"
    echo ""
    echo "Models are now stored in: $MODELS_DIR"
    echo "You can remove the old models directory at: $INSTALL_DIR/models"
    echo ""
else
    print_error "Containers failed to start"
    echo "Check logs with: docker logs vllm-router"
    exit 1
fi
