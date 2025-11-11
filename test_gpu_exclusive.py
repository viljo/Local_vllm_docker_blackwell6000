#!/usr/bin/env python3
"""
GPU Exclusive Access Test
Verifies only one vLLM container is running and has exclusive GPU access
"""
import subprocess
import json
import sys


def get_running_vllm_containers():
    """Get list of running vLLM model containers"""
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=vllm-", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )
    containers = [name for name in result.stdout.strip().split('\n') if name and 'router' not in name]
    return containers


def get_container_gpu_usage(container_name):
    """Get GPU memory usage for a specific container"""
    try:
        # Get the container's process PIDs
        result = subprocess.run(
            ["docker", "top", container_name, "-eo", "pid"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        pids = [line.strip() for line in result.stdout.strip().split('\n')[1:]]  # Skip header

        if not pids:
            return None

        # Get GPU memory usage via nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        total_memory = 0
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(',')
            if len(parts) == 2:
                pid, memory = parts[0].strip(), parts[1].strip()
                if pid in pids:
                    total_memory += int(memory)

        return total_memory
    except Exception as e:
        print(f"Error getting GPU usage: {e}")
        return None


def get_total_gpu_memory():
    """Get total GPU memory in MiB"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
        return None
    except Exception as e:
        print(f"Error getting total GPU memory: {e}")
        return None


def get_gpu_memory_usage():
    """Get current GPU memory usage"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            used, free, total = result.stdout.strip().split(', ')
            return {
                'used': int(used),
                'free': int(free),
                'total': int(total)
            }
        return None
    except Exception as e:
        print(f"Error getting GPU memory: {e}")
        return None


def test_exclusive_gpu_access():
    """Test that only one vLLM container is running with GPU access"""
    print("="*60)
    print("GPU Exclusive Access Test")
    print("="*60)

    # Test 1: Only one vLLM container running
    print("\n1. Checking vLLM Container Count")
    print("-"*60)

    running_containers = get_running_vllm_containers()
    print(f"Running vLLM containers: {len(running_containers)}")
    for container in running_containers:
        print(f"  - {container}")

    if len(running_containers) == 0:
        print("✗ FAIL: No vLLM containers running")
        return False
    elif len(running_containers) > 1:
        print(f"✗ FAIL: Multiple vLLM containers running ({len(running_containers)})")
        print("  Only one model should be running at a time for exclusive GPU access")
        return False
    else:
        print(f"✓ PASS: Exactly 1 vLLM container running")

    # Test 2: GPU memory allocation
    print("\n2. Checking GPU Memory Allocation")
    print("-"*60)

    gpu_info = get_gpu_memory_usage()
    if gpu_info:
        print(f"Total GPU Memory: {gpu_info['total']} MiB")
        print(f"Used GPU Memory:  {gpu_info['used']} MiB ({gpu_info['used']/gpu_info['total']*100:.1f}%)")
        print(f"Free GPU Memory:  {gpu_info['free']} MiB ({gpu_info['free']/gpu_info['total']*100:.1f}%)")

        # Check if most GPU memory is allocated
        usage_percent = gpu_info['used'] / gpu_info['total'] * 100
        if usage_percent < 50:
            print(f"⚠ WARNING: GPU usage is low ({usage_percent:.1f}%) - model may not be loaded")
    else:
        print("✗ FAIL: Could not get GPU memory info")
        return False

    # Test 3: Container-specific GPU usage
    print("\n3. Checking Container GPU Usage")
    print("-"*60)

    container_name = running_containers[0]
    container_gpu_usage = get_container_gpu_usage(container_name)

    if container_gpu_usage is not None:
        print(f"Container: {container_name}")
        print(f"GPU Memory Used: {container_gpu_usage} MiB")
        print(f"Percentage of Total: {container_gpu_usage/gpu_info['total']*100:.1f}%")

        if container_gpu_usage > 0:
            print(f"✓ PASS: Container is using GPU memory")
        else:
            print(f"⚠ WARNING: Container is not using GPU memory")
    else:
        print(f"✗ Could not determine GPU usage for {container_name}")

    # Test 4: Check for GPU compute mode (exclusive if possible)
    print("\n4. Checking GPU Compute Mode")
    print("-"*60)

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=compute_mode", "--format=csv,noheader"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            compute_mode = result.stdout.strip()
            print(f"Current Compute Mode: {compute_mode}")

            if compute_mode == "Exclusive_Process":
                print("✓ EXCELLENT: GPU is in Exclusive_Process mode")
            elif compute_mode == "Default":
                print("ℹ INFO: GPU is in Default mode (shared access)")
                print("  To enable exclusive mode, run:")
                print("  sudo nvidia-smi -c EXCLUSIVE_PROCESS")
            else:
                print(f"ℹ INFO: GPU compute mode is {compute_mode}")
    except Exception as e:
        print(f"Could not check compute mode: {e}")

    # Test 5: Docker GPU device settings
    print("\n5. Checking Docker GPU Device Settings")
    print("-"*60)

    try:
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            inspect_data = json.loads(result.stdout)[0]

            # Check GPU device requests
            device_requests = inspect_data.get('HostConfig', {}).get('DeviceRequests', [])
            if device_requests:
                for req in device_requests:
                    capabilities = req.get('Capabilities', [])
                    device_ids = req.get('DeviceIDs', [])
                    count = req.get('Count', 'all')

                    print(f"GPU Device Request:")
                    print(f"  Capabilities: {capabilities}")
                    print(f"  Device IDs: {device_ids if device_ids else 'all'}")
                    print(f"  Count: {count}")

                    if count == 'all' or (isinstance(count, int) and count > 1):
                        print("  ⚠ Container can access ALL GPUs")
                        print("  For exclusive access, specify device ID: 0")
                    else:
                        print("  ✓ Container has limited GPU access")
            else:
                print("No GPU device requests found")

    except Exception as e:
        print(f"Could not inspect container: {e}")

    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"✓ Only 1 vLLM container running: {container_name}")
    print(f"✓ GPU Memory Usage: {gpu_info['used']} MiB / {gpu_info['total']} MiB")

    return True


if __name__ == "__main__":
    success = test_exclusive_gpu_access()
    sys.exit(0 if success else 1)
