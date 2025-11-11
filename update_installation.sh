#!/bin/bash
set -e

#==============================================================================
# Update Installation Script
# Updates the /opt/local_llm_service installation with latest changes
#==============================================================================

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

INSTALL_DIR="/opt/local_llm_service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_info "Updating installation at $INSTALL_DIR..."

# Stop the service
print_info "Stopping service..."
systemctl stop local-llm-service

# Backup current .env
print_info "Backing up .env file..."
cp "$INSTALL_DIR/.env" "$INSTALL_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"

# Preserve API key
EXISTING_API_KEY=$(grep "^API_KEY=" "$INSTALL_DIR/.env" | cut -d'=' -f2-)

# Copy updated files (excluding .git, models, etc.)
print_info "Copying updated files..."
rsync -av --exclude='.git' \
          --exclude='node_modules' \
          --exclude='__pycache__' \
          --exclude='*.pyc' \
          --exclude='.env' \
          --exclude='.env.backup*' \
          --exclude='models/' \
          "$SCRIPT_DIR/" "$INSTALL_DIR/"

# Update .env with new variables while preserving API key
print_info "Updating .env file..."
cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env.new"
sed -i "s/sk-local-your-secret-key-here/$EXISTING_API_KEY/" "$INSTALL_DIR/.env.new"
mv "$INSTALL_DIR/.env.new" "$INSTALL_DIR/.env"

# Set ownership
chown -R root:root "$INSTALL_DIR"

# Rebuild frontend with correct API key
print_info "Rebuilding frontend container with API key from .env..."
cd "$INSTALL_DIR"
docker compose build webui-frontend

print_success "Frontend container rebuilt with correct API key"

# Restart the service
print_info "Restarting service..."
systemctl start local-llm-service

print_success "Installation updated successfully!"
print_info "API key preserved: $EXISTING_API_KEY"
echo ""
print_info "Check service status: systemctl status local-llm-service"
print_info "View logs: journalctl -u local-llm-service -f"
