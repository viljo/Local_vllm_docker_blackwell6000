#!/bin/bash
# Setup script for GPU exclusive access mode

echo "=========================================="
echo "GPU Exclusive Access Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    echo ""
    echo "Usage:"
    echo "  sudo ./setup_gpu_exclusive.sh"
    exit 1
fi

# Get GPU information
echo "1. Detecting GPUs..."
nvidia-smi -L

# Check current compute mode
echo ""
echo "2. Current GPU Compute Mode:"
nvidia-smi --query-gpu=index,compute_mode --format=csv

# Set exclusive process mode
echo ""
echo "3. Setting GPU 0 to EXCLUSIVE_PROCESS mode..."
nvidia-smi -i 0 -c EXCLUSIVE_PROCESS

if [ $? -eq 0 ]; then
    echo "✓ GPU 0 is now in EXCLUSIVE_PROCESS mode"
else
    echo "✗ Failed to set exclusive mode"
    exit 1
fi

# Verify
echo ""
echo "4. Verifying GPU Compute Mode:"
nvidia-smi --query-gpu=index,compute_mode --format=csv

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "GPU 0 is now configured for exclusive access."
echo "Only one process can use the GPU at a time."
echo ""
echo "To revert to default (shared) mode, run:"
echo "  sudo nvidia-smi -i 0 -c DEFAULT"
echo ""
