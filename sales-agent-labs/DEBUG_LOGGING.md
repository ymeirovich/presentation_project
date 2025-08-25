# GCP Debug Logging

## Quick Setup for Debugging Timeouts

### 1. Enable Local GCP Debug Logging (FREE)
```bash
# Add to your .env file
ENABLE_GCP_DEBUG_LOGGING=true
```

This will show you detailed logs for:
- ✅ Google API authentication 
- ✅ HTTP requests/responses to GCP APIs
- ✅ Vertex AI API calls (Gemini LLM, Imagen)
- ✅ Google Slides API calls
- ✅ Google Drive API uploads
- ✅ Network timeouts and retries

**Cost: $0** - All logs stay local

### 2. Enable Cloud Logging (COSTS MONEY)
```bash
# Add to your .env file  
ENABLE_CLOUD_LOGGING=true
```

**Only use for production debugging** - sends all logs to GCP Cloud Logging.

**Cost: ~$0.50/GB** - Use sparingly!

## Debug Your Timeout Issues

### Step 1: Enable debug logging
```bash
echo "ENABLE_GCP_DEBUG_LOGGING=true" >> .env
```

### Step 2: Run a test presentation
```bash
python -m src.service.http
# Trigger a presentation generation via Slack or API
```

### Step 3: Analyze the logs
Look for patterns like:

**Timeout in auth:**
```
DEBUG:google.auth:Failed to retrieve token: timeout
```

**Timeout in API call:**
```  
DEBUG:google.api_core:Request timeout after 60s
```

**Slow Drive upload:**
```
DEBUG:googleapiclient:POST /upload/drive/v3/files took 180s
```

**Vertex AI delays:**
```
DEBUG:google.cloud:Vertex AI request took 45s
```

### Step 4: Correlate with your app logs
Match `gcp_trace_id` in your app logs with GCP debug logs to see the full request flow.

## Disable When Done

```bash
# Comment out or remove from .env
# ENABLE_GCP_DEBUG_LOGGING=true
```

This keeps your logs clean and performance optimal for normal operation.