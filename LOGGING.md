# API Logging and Error Tracking

**Updated**: 2025-11-12

## Quick Reference

### View Logs

```bash
# View last 50 lines
./scripts/view-logs.sh

# View all errors
./scripts/view-logs.sh errors

# View warnings
./scripts/view-logs.sh warnings

# Follow logs in real-time
./scripts/view-logs.sh tail

# View logs from last 10 minutes
./scripts/view-logs.sh since 10m

# View specific request by ID
./scripts/view-logs.sh request abc123

# View chat completion requests
./scripts/view-logs.sh chat

# View tool-related logs
./scripts/view-logs.sh tools

# View authentication failures
./scripts/view-logs.sh auth
```

### Analyze Errors

```bash
# Analyze errors from last hour (default)
./scripts/analyze-errors.sh

# Analyze errors from last 5 minutes
./scripts/analyze-errors.sh 5m

# Analyze errors from last 24 hours
./scripts/analyze-errors.sh 24h

# Analyze errors since specific date
./scripts/analyze-errors.sh "2025-11-12 10:00"
```

### Direct Docker Commands

```bash
# View all logs
docker logs vllm-router

# Follow logs (real-time)
docker logs vllm-router -f

# Last 100 lines
docker logs vllm-router --tail 100

# Logs from last 30 minutes
docker logs vllm-router --since 30m

# Search for specific text
docker logs vllm-router | grep "ERROR"

# Save logs to file
docker logs vllm-router > router-logs.txt
```

## Log Levels

Configure log verbosity with the `LOG_LEVEL` environment variable:

```bash
# In docker-compose.yml or .env
LOG_LEVEL=DEBUG   # Most verbose - all logs
LOG_LEVEL=INFO    # Default - normal operations
LOG_LEVEL=WARNING # Only warnings and errors
LOG_LEVEL=ERROR   # Only errors
```

## Understanding Log Format

```
2025-11-12 14:10:30 - app.main - INFO - [request-id] Message
     ^                  ^          ^            ^
     |                  |          |            |
  Timestamp          Module    Log Level   Request ID (for tracking)
```

### Log Levels Explained

- **DEBUG**: Detailed diagnostic information
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Something unexpected happened, but the application is still working
- **ERROR**: Due to a more serious problem, the application couldn't perform a function

## Common Error Patterns

### 1. Authentication Errors

```
WARNING - Invalid API key attempt
```

**Cause**: Client using wrong API key
**Fix**: Check API key on remote clients (should be `sk-local-58511ab0d37124beb566b567e54b8307`)

### 2. Backend Errors

```
ERROR - Backend error: {"error": ...}
```

**Cause**: Model service (vllm-gpt-oss-120b, etc.) is down or returning errors
**Fix**:
```bash
docker ps | grep vllm
docker logs vllm-gpt-oss-120b
docker restart vllm-gpt-oss-120b
```

### 3. Timeout Errors

```
ERROR - Request timeout after 300.0s
```

**Cause**: Model taking too long to respond
**Fix**: Model may be overloaded or stuck. Check GPU usage:
```bash
docker exec vllm-gpt-oss-120b nvidia-smi
```

### 4. Tool Validation Errors

```
ERROR - Tool validation error: Tool message references unknown tool_call_id
```

**Cause**: Client sent tool result without corresponding tool call
**Fix**: This is expected validation - client needs to include tool_call in assistant message before tool result

### 5. Connection Errors

```
ERROR - Backend unavailable: Connection refused
```

**Cause**: Backend model service not running
**Fix**:
```bash
docker ps | grep vllm
docker compose up -d vllm-gpt-oss-120b
```

## Tracking Specific Requests

Every chat completion request gets a unique ID. Use it to trace the entire request lifecycle:

```bash
# Find the request ID from logs
./scripts/view-logs.sh chat | grep "your search term"

# View all logs for that request
./scripts/view-logs.sh request <REQUEST_ID>
```

Example:
```
2025-11-12 14:10:30 - app.main - INFO - [abc123def456] Chat completion request - model=gpt-oss-120b
2025-11-12 14:10:30 - app.main - INFO - [abc123def456] Routing to backend: http://vllm-gpt-oss-120b:8000
2025-11-12 14:10:31 - app.main - INFO - [abc123def456] Tool calls detected: 1
```

## Monitoring Tips

### 1. Watch for Errors in Real-Time

```bash
./scripts/view-logs.sh tail | grep --color=always ERROR
```

### 2. Monitor Authentication Failures

```bash
watch -n 5 './scripts/view-logs.sh auth | tail -10'
```

### 3. Check Error Rate

```bash
# Run every hour to track error trends
./scripts/analyze-errors.sh 1h > /tmp/error-report-$(date +%Y%m%d-%H%M).txt
```

### 4. Alert on Critical Errors

```bash
# Add to cron for monitoring
#!/bin/bash
ERROR_COUNT=$(docker logs vllm-router --since 5m 2>&1 | grep -c "ERROR")
if [ "$ERROR_COUNT" -gt 10 ]; then
    echo "High error rate detected: $ERROR_COUNT errors in last 5 minutes"
    # Send alert (email, webhook, etc.)
fi
```

## Log Rotation

Docker automatically rotates logs. Configure in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Debugging Workflow

1. **Check if error exists**:
   ```bash
   ./scripts/analyze-errors.sh 1h
   ```

2. **View detailed errors**:
   ```bash
   ./scripts/view-logs.sh errors
   ```

3. **Find specific request**:
   ```bash
   ./scripts/view-logs.sh request <ID>
   ```

4. **Check backend status**:
   ```bash
   docker ps | grep vllm
   ```

5. **Review backend logs** (if needed):
   ```bash
   docker logs vllm-gpt-oss-120b --tail 50
   ```

## Performance Monitoring

### Request Volume

```bash
# Count requests in last hour
docker logs vllm-router --since 1h 2>&1 | grep "Chat completion request" | wc -l
```

### Average Response Time

```bash
# Look for slow requests (adjust grep pattern based on your needs)
docker logs vllm-router --since 1h 2>&1 | grep -E "completed in [0-9]+\.[0-9]+s"
```

### Tool Usage Stats

```bash
# Count tool calls
docker logs vllm-router --since 1h 2>&1 | grep "Detected.*tool call" | wc -l
```

## Troubleshooting Guide

### No Logs Appearing

```bash
# Check if container is running
docker ps | grep vllm-router

# Check container logs directly
docker logs vllm-router

# Restart container
docker restart vllm-router
```

### Logs Too Verbose

```bash
# Set log level to WARNING
docker exec vllm-router sh -c 'echo "LOG_LEVEL=WARNING" >> /app/.env'
docker restart vllm-router
```

### Logs Filling Disk

```bash
# Check log size
docker inspect vllm-router --format='{{.LogPath}}' | xargs ls -lh

# Clear logs (WARNING: deletes all logs)
docker exec vllm-router truncate -s 0 $(docker inspect --format='{{.LogPath}}' vllm-router)
```

## Support

For more information:
- API Documentation: `specs/003-cline-tool-calling/`
- Troubleshooting: `CLINE_TROUBLESHOOTING.md`
- Test Scripts: `test_tool_calling_curl.sh`

---

**Last Updated**: 2025-11-12
**Feature**: Tool Calling with Enhanced Logging (003-cline-tool-calling)
