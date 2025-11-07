# Testing the Installation Script

## Prerequisites

Before testing the installation script, ensure you have:

1. **Sudo Access**: You will need root/sudo privileges
2. **Clean System**: For best results, test on a fresh Debian 13 installation
3. **Backups**: If testing on an existing system, backup important data

## Pre-Installation Verification

### 1. Verify Script Syntax

```bash
# Check installation script
bash -n install_debian.sh
# Should output: (nothing if valid)

# Check uninstall script
bash -n uninstall_debian.sh
# Should output: (nothing if valid)
```

### 2. Check Prerequisites

```bash
# Check if Docker is installed
docker --version

# Check NVIDIA GPU
nvidia-smi

# Check Git
git --version
```

## Installation Test Procedure

### Step 1: Stop Current Services (if running)

```bash
# If you're currently running from the dev directory
cd /home/asvil/git/local_llm_service
docker compose down

# Stop any model containers
docker stop vllm-gpt-oss-120b vllm-gpt-oss-20b vllm-coder vllm-general 2>/dev/null || true
```

### Step 2: Run the Installation Script

```bash
# Run with sudo
sudo ./install_debian.sh
```

**Expected Output:**

```
[INFO] Starting Local vLLM Service installation on Debian 13...
[INFO] Checking system requirements...
[SUCCESS] NVIDIA GPU detected: NVIDIA RTX PRO 6000 ...
[INFO] Installing Docker...
[SUCCESS] Docker is already installed (or newly installed)
[INFO] Installing NVIDIA Container Toolkit...
[SUCCESS] NVIDIA Container Toolkit installed and configured
[INFO] Setting up service in /opt/local_llm_service...
[SUCCESS] Service files copied to /opt/local_llm_service
[INFO] Creating systemd service...
[SUCCESS] Systemd service created
[INFO] Enabling and starting service...
[SUCCESS] Service enabled and started
[INFO] Waiting for services to start...
[SUCCESS] Service is running

========================================================================
✅ Local vLLM Service installed successfully!
========================================================================
```

### Step 3: Verify Installation

Run the automated test script:

```bash
./test_installation.sh
```

**Expected Output:**

```
========================================================================
Installation Test Suite
========================================================================

[TEST] Checking installation directory...
[PASS] Installation directory exists: /opt/local_llm_service
[TEST] Checking docker-compose.yml...
[PASS] docker-compose.yml found
[TEST] Checking systemd service...
[PASS] Systemd service file exists
[TEST] Checking if service is enabled...
[PASS] Service is enabled for autostart
[TEST] Checking if service is running...
[PASS] Service is active
[TEST] Checking Docker containers...
[PASS] Docker containers are running (3 containers)
[TEST] Checking WebUI accessibility...
[PASS] WebUI is accessible at http://localhost:3000
[TEST] Checking API accessibility...
[PASS] API is accessible at http://localhost:8080
[TEST] Checking GPU access in containers...
[PASS] GPU is accessible in containers
[TEST] Checking autostart configuration...
[PASS] Service is configured to start after boot

========================================================================
✅ All tests passed!
Installation is working correctly.
========================================================================
```

### Step 4: Manual Verification

#### Check Service Status

```bash
sudo systemctl status local-llm-service
```

Expected output includes:
- `Active: active (running)`
- `Loaded: loaded (/etc/systemd/system/local-llm-service.service; enabled)`

#### Check Running Containers

```bash
cd /opt/local_llm_service
docker compose ps
```

Should show:
- `vllm-router` - Running (healthy)
- `webui-frontend` - Running
- One or more model containers (e.g., `vllm-gpt-oss-120b`)

#### Check Logs

```bash
# System logs
sudo journalctl -u local-llm-service -n 50

# Container logs
cd /opt/local_llm_service
docker compose logs -f
```

Look for:
- "Auto-starting largest downloaded model"
- "Successfully started gpt-oss-120b" (or similar)
- No error messages

#### Access WebUI

Open browser and navigate to:
- http://localhost:3000

You should see the Local LLM Chat interface.

#### Test API

```bash
# Health check
curl http://localhost:8080/health

# Model status
curl http://localhost:8080/v1/models/status | jq .
```

### Step 5: Test Autostart After Reboot

```bash
# Reboot the system
sudo reboot

# After reboot, check if service started automatically
sudo systemctl status local-llm-service

# Should show "active (running)"
```

## Uninstallation Test

### Test Standard Uninstall

```bash
sudo ./uninstall_debian.sh
```

When prompted, type `yes` and press Enter.

**Verify uninstallation:**

```bash
# Service should not exist
sudo systemctl status local-llm-service
# Should show: "could not be found"

# Directory should be removed
ls /opt/local_llm_service
# Should show: "No such file or directory"

# Containers should be stopped
docker ps --filter "name=vllm-"
# Should show: empty list (just headers)
```

### Test Uninstall with Data Preservation

```bash
# First, install again
sudo ./install_debian.sh

# Wait for models to download (if applicable)
sleep 60

# Uninstall but keep data
sudo ./uninstall_debian.sh --keep-data
```

When prompted, type `yes` and press Enter.

**Verify data preservation:**

```bash
# Check for backup directory
ls -la /opt/ | grep "local_llm_service.backup"
# Should show: backup directory with timestamp

# Check models were preserved
ls /opt/local_llm_service.backup-*/models
# Should show: models directory with data
```

## Troubleshooting Common Issues

### Issue: "Docker is not installed"

**Solution:**
```bash
# The script should install Docker automatically
# If it fails, check logs:
sudo journalctl -xe | grep docker
```

### Issue: "NVIDIA GPU not detected"

**Solution:**
```bash
# Check NVIDIA drivers
nvidia-smi

# If not working, install drivers first:
sudo apt-get update
sudo apt-get install -y nvidia-driver-550
sudo reboot
```

### Issue: "Service fails to start"

**Solution:**
```bash
# Check detailed logs
sudo journalctl -u local-llm-service -n 100 --no-pager

# Check Docker status
sudo systemctl status docker

# Verify NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

### Issue: "Containers stuck in 'starting' state"

**Solution:**
```bash
# Check container logs
cd /opt/local_llm_service
docker compose logs vllm-router
docker compose logs vllm-gpt-oss-120b

# Common causes:
# - Insufficient GPU memory
# - Model files not downloaded
# - Network issues
```

### Issue: "Port already in use"

**Solution:**
```bash
# Check what's using the ports
sudo lsof -i :3000
sudo lsof -i :8080

# Kill conflicting processes or change ports in docker-compose.yml
```

## Test Results Checklist

After running all tests, verify:

- [ ] Installation script completes without errors
- [ ] Systemd service is created and enabled
- [ ] Containers start successfully
- [ ] WebUI is accessible
- [ ] API endpoints respond
- [ ] GPU is accessible in containers
- [ ] Service survives reboot (autostart works)
- [ ] Uninstallation removes all components
- [ ] `--keep-data` flag preserves model data

## Report Issues

If you encounter issues during testing:

1. **Collect logs:**
   ```bash
   sudo journalctl -u local-llm-service -n 200 > install_test_logs.txt
   docker compose logs >> install_test_logs.txt
   ```

2. **System information:**
   ```bash
   uname -a > system_info.txt
   docker --version >> system_info.txt
   nvidia-smi >> system_info.txt
   ```

3. **Create GitHub issue** with:
   - Description of the problem
   - Installation logs
   - System information
   - Steps to reproduce

## Success Criteria

Installation is considered successful if:

1. ✅ All automated tests pass (`./test_installation.sh`)
2. ✅ WebUI is accessible and functional
3. ✅ Models can be loaded and switched
4. ✅ Service auto-starts after reboot
5. ✅ Uninstallation cleanly removes all components
6. ✅ No errors in logs

---

**Note:** This guide is for testing purposes. For production deployment, review and adjust settings in `/opt/local_llm_service/docker-compose.yml` and `router/app/config.py` as needed.
