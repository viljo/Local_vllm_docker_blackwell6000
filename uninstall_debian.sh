#!/bin/bash
set -e

#==============================================================================
# Local vLLM Service - Debian 13 Uninstallation Script
#==============================================================================
# This script removes the Local vLLM Service from /opt/local_llm_service
# and disables the systemd service.
#
# Usage:
#   sudo ./uninstall_debian.sh
#
# Options:
#   --keep-data    Keep model data and configuration
#==============================================================================

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation configuration
INSTALL_DIR="/opt/local_llm_service"
MODELS_DIR="/ssd/LLMs"
SERVICE_NAME="local-llm-service"
KEEP_DATA=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-data)
            KEEP_DATA=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to print colored messages
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
print_warning "Local vLLM Service Uninstallation"
echo "========================================================================"
echo ""
echo "This will remove:"
echo "  - Service files from $INSTALL_DIR"
echo "  - Systemd service $SERVICE_NAME"
echo "  - All running containers"
echo ""

if [[ "$KEEP_DATA" == true ]]; then
    print_info "Model data in $MODELS_DIR will be preserved (--keep-data flag set)"
else
    print_warning "Model data in $MODELS_DIR will be DELETED"
fi

echo ""
read -p "Are you sure you want to uninstall? (yes/NO): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    print_info "Uninstallation cancelled"
    exit 0
fi

#==============================================================================
# Step 1: Stop and disable service
#==============================================================================
print_info "Stopping and disabling service..."

if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
    print_success "Service stopped"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    systemctl disable "$SERVICE_NAME"
    print_success "Service disabled"
fi

#==============================================================================
# Step 2: Stop all containers
#==============================================================================
if [[ -d "$INSTALL_DIR" ]]; then
    print_info "Stopping all containers..."
    cd "$INSTALL_DIR"

    if [[ -f "docker-compose.yml" ]]; then
        docker compose down -v 2>/dev/null || true
        print_success "Containers stopped"
    fi
fi

#==============================================================================
# Step 3: Remove systemd service
#==============================================================================
print_info "Removing systemd service..."

if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
    rm "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    print_success "Systemd service removed"
fi

#==============================================================================
# Step 4: Remove installation directory
#==============================================================================
print_info "Removing installation directory..."

if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    print_success "Installation directory removed"
fi

#==============================================================================
# Step 5: Handle models directory
#==============================================================================
if [[ -d "$MODELS_DIR" ]]; then
    if [[ "$KEEP_DATA" == true ]]; then
        print_info "Keeping model data in $MODELS_DIR (--keep-data flag set)"
        print_success "Model data preserved at $MODELS_DIR"
    else
        read -p "Delete all models in $MODELS_DIR? (yes/NO): " -r
        echo
        if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            print_info "Removing models directory..."
            rm -rf "$MODELS_DIR"
            print_success "Models directory removed"
        else
            print_info "Keeping models directory at $MODELS_DIR"
        fi
    fi
fi

#==============================================================================
# Step 6: Clean up Docker resources (optional)
#==============================================================================
print_info "Cleaning up Docker resources..."

# Remove dangling images
docker image prune -f > /dev/null 2>&1 || true

# Show remaining vLLM containers/images
VLLM_CONTAINERS=$(docker ps -a --filter "name=vllm-" --format "{{.Names}}" 2>/dev/null | wc -l)
VLLM_IMAGES=$(docker images --filter "reference=*vllm*" --format "{{.Repository}}" 2>/dev/null | wc -l)

if [[ $VLLM_CONTAINERS -gt 0 ]] || [[ $VLLM_IMAGES -gt 0 ]]; then
    echo ""
    print_warning "Found remaining Docker resources:"
    [[ $VLLM_CONTAINERS -gt 0 ]] && echo "  - $VLLM_CONTAINERS vLLM container(s)"
    [[ $VLLM_IMAGES -gt 0 ]] && echo "  - $VLLM_IMAGES vLLM image(s)"
    echo ""
    read -p "Remove these as well? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker ps -a --filter "name=vllm-" -q | xargs -r docker rm -f
        docker images --filter "reference=*vllm*" -q | xargs -r docker rmi -f
        print_success "Docker resources removed"
    fi
fi

#==============================================================================
# Uninstallation Complete
#==============================================================================
echo ""
echo "========================================================================"
print_success "Local vLLM Service uninstalled successfully!"
echo "========================================================================"
echo ""

if [[ "$KEEP_DATA" == true ]] && [[ -d "$MODELS_DIR" ]]; then
    echo "Model data preserved at: $MODELS_DIR"
    echo ""
fi

echo "The following were NOT removed (manual cleanup if desired):"
echo "  - Docker Engine"
echo "  - NVIDIA Container Toolkit"
echo "  - NVIDIA Drivers"
echo ""
echo "To reinstall, run: sudo ./install_debian.sh"
echo ""
echo "========================================================================"
