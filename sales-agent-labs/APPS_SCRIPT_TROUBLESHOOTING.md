# Apps Script Speaker Notes Troubleshooting Guide

## Problem Summary

**Issue**: `ACCESS_TOKEN_SCOPE_INSUFFICIENT` error when calling Google Apps Script API
**Root Cause**: Apps Script requires additional OAuth scopes that aren't automatically granted

## Current Status

✅ **OAuth Token Scopes**: `["presentations", "drive.file", "script.projects"]`  
❌ **Apps Script Execution**: Failing due to insufficient scopes  
✅ **Native API Fallback**: Enhanced implementation ready  

## Solutions (In Priority Order)

### 🔧 Solution 1: Fix Apps Script Manifest (Recommended)

The Apps Script project needs an `appsscript.json` manifest file:

1. **Open Apps Script Project**: 
   ```
   https://script.google.com/d/1btsd9u4hMEqJR5pyA66OiC_1DSjqUiGLNlfa_lWLB1W5gcGELxi6de2q/edit
   ```

2. **Add Manifest File** (`appsscript.json`):
   ```json
   {
     "timeZone": "America/New_York",
     "dependencies": {
       "enabledAdvancedServices": [
         {
           "userSymbol": "Slides",
           "serviceId": "slides", 
           "version": "v1"
         }
       ]
     },
     "oauthScopes": [
       "https://www.googleapis.com/auth/presentations",
       "https://www.googleapis.com/auth/script.projects"
     ],
     "runtimeVersion": "V8"
   }
   ```

3. **Save and Deploy**:
   - Save the manifest file
   - Create a new deployment or update existing one
   - Test the script manually in the Apps Script editor

4. **Force OAuth Re-consent**:
   ```bash
   FORCE_OAUTH_CONSENT=1 python -m src.mcp_lab examples/report_demo.txt
   ```

### 🎯 Solution 2: Enhanced Native API (Already Implemented)

The codebase now uses a robust 4-strategy approach:

1. **Enhanced Native API** (Primary) - Multiple fallback methods
2. **Apps Script** (Secondary) - If properly configured  
3. **Legacy Native** (Tertiary) - Original implementation
4. **Visible Script Box** (Guaranteed) - Always works

**Files Added**:
- `/src/agent/notes_native_api.py` - Enhanced native implementation
- `SetNotes_Enhanced.js` - Improved Apps Script with error handling
- Updated `/src/agent/slides_google.py` - Multi-strategy approach

### 🔍 Solution 3: Apps Script Deployment Fix

If manifest approach fails, try deployment-level fixes:

1. **Check Apps Script Project Settings**:
   - Ensure project is deployed as "Execute as: Me"
   - Set "Who has access: Anyone"
   - Verify the Script ID matches environment variable

2. **OAuth Scope Investigation**:
   ```bash
   # Check current token scopes
   python3 -c "
   from src.agent.slides_google import _load_credentials
   creds = _load_credentials()
   print('Current scopes:', getattr(creds, 'scopes', []))
   "
   ```

3. **Manual Apps Script Test**:
   - Open Apps Script editor
   - Run `testAccess()` function manually
   - Check execution logs for permission errors

### 📋 Solution 4: Alternative Authentication

If Apps Script remains problematic, use service account approach:

1. **Service Account for Apps Script**:
   ```bash
   # Enable Apps Script API for service account
   gcloud services enable script.googleapis.com --project=presgen
   ```

2. **Domain-Wide Delegation** (Enterprise only):
   - Configure service account with domain-wide delegation
   - Add required scopes in Google Workspace Admin Console

## Testing & Verification

### Test Enhanced Native Implementation
```bash
python3 -c "
from src.agent.notes_native_api import test_notes_implementation
result = test_notes_implementation('PRESENTATION_ID', 'SLIDE_ID')
print('Test result:', result)
"
```

### Test Apps Script Directly
```bash
python3 -c "
import os
from src.agent.slides_google import _load_credentials
from src.agent.notes_apps_script import set_speaker_notes_via_script
creds = _load_credentials()
result = set_speaker_notes_via_script(
    creds, 
    os.environ['APPS_SCRIPT_SCRIPT_ID'],
    'test_pres_id',
    'test_slide_id', 
    'Test notes'
)
print('Apps Script result:', result)
"
```

### Full Integration Test
```bash
python -m src.mcp_lab examples/report_demo.txt --slides 1 --no-cache
```

## Configuration Check

### Required Environment Variables
```bash
APPS_SCRIPT_SCRIPT_ID=1btsd9u4hMEqJR5pyA66OiC_1DSjqUiGLNlfa_lWLB1W5gcGELxi6de2q
GOOGLE_CLOUD_PROJECT=presgen
OAUTH_CLIENT_JSON=oauth_slides_client.json
```

### OAuth Scopes Required
```
https://www.googleapis.com/auth/presentations
https://www.googleapis.com/auth/drive.file  
https://www.googleapis.com/auth/script.projects
```

## Error Patterns & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `ACCESS_TOKEN_SCOPE_INSUFFICIENT` | Missing Apps Script manifest scopes | Add `appsscript.json` with required scopes |
| `PERMISSION_DENIED` | Apps Script not deployed properly | Check deployment settings and permissions |
| `Script not found` | Wrong Script ID | Verify `APPS_SCRIPT_SCRIPT_ID` environment variable |
| `Slides API not enabled` | Missing API access | Enable Slides API in Google Cloud Console |

## Current Implementation Status

✅ **Multi-strategy approach implemented**  
✅ **Enhanced native API with 4 fallback methods**  
✅ **Guaranteed fallback (visible script box)**  
🔧 **Apps Script requires manifest fix**  
📋 **Testing scripts ready**  

## Next Steps

1. **Immediate**: Use enhanced native API (already active)
2. **Short-term**: Fix Apps Script manifest for optimal experience
3. **Long-term**: Consider service account approach for production

The system now works reliably with multiple fallbacks, making the Apps Script issue non-blocking while still providing a path to optimal implementation.