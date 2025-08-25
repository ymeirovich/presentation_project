# PresGen Project Context & Status

**Last Updated**: January 2025  
**Current Status**: PresGen-Data feature complete, ready for production deployment

## Project Goal
PresGen is an AI-powered SaaS platform that transforms unstructured reports and spreadsheet data into polished Google Slides presentations through intelligent summarization, data visualization, and automated slide generation.

## Core User Story
**Who**: Sales teams, consultants, and business analysts who need to create client presentations quickly  
**Problem**: Manual slide creation from reports and data analysis is time-consuming and inconsistent  
**Solution**: One-command transformation from raw text + data → professional presentation decks with charts, insights, and structured content

## Technology Stack

### Backend
- **Python 3.13** - Core runtime
- **FastAPI** - HTTP API server with async support
- **MCP (Model Context Protocol)** - JSON-RPC tooling architecture for AI agent orchestration
- **DuckDB + Pandas** - Local data processing and SQL query engine
- **Pydantic** - Data validation and schema enforcement

### AI & Cloud Services
- **Google Vertex AI** - Gemini 2.0 Flash for summarization, Imagen for image generation
- **Google Slides API** - Programmatic deck creation and slide insertion
- **Google Drive API** - Image hosting and file sharing

### Data & Storage
- **Parquet** - Columnar storage for uploaded datasets (local: `out/data/`, prod: GCS)
- **Local file system** - Development artifacts and caching (prod: Cloud Storage)
- **JSON** - Configuration, logging, and state management

### Deployment & Operations
- **Uvicorn** - ASGI server (local dev)
- **ngrok** - Local HTTPS tunneling for Slack integration (dev)
- **Docker + Cloud Run** - Production containerized deployment (planned)
- **Slack Apps** - Primary user interface via slash commands

## Key Architectural Decisions

### 1. MCP-Based Tool Architecture
**Decision**: Built orchestrator using Model Context Protocol (JSON-RPC over stdio) instead of direct function calls  
**Why**: Provides clean separation between AI tools, enables subprocess isolation, and allows for distributed tool execution. Each tool (LLM, Imagen, Slides) is independently testable and can be scaled separately.

### 2. Three-Feature Modular Design
**Decision**: Split into PresGen (text→slides), PresGen-Data (spreadsheets→insights→slides), and PresGen-Video (video→timed slides)  
**Why**: Each feature has distinct user workflows and technical requirements. Modular approach allows independent development and deployment while sharing common infrastructure.

### 3. Smart Slide Allocation Strategy  
**Decision**: Dynamically distribute requested slide count between narrative and data slides rather than fixed allocation  
**Why**: User expectations vary - sometimes they want data-heavy presentations, sometimes narrative-focused. Algorithm reserves at least 1 narrative slide but adapts to content availability.

### 4. Pattern-First NL→SQL with LLM Fallback
**Decision**: Use regex patterns for common data queries ("Total sales by company") with Gemini LLM as fallback  
**Why**: Patterns are fast, predictable, and don't consume API quotas. LLM handles edge cases. This hybrid approach balances reliability with flexibility.

### 5. Drive-Based Image Strategy
**Decision**: Upload all images (charts, AI-generated) to Google Drive, then insert by `drive_file_id` rather than public URLs  
**Why**: Slides API has reliability issues with external URLs. Drive integration ensures images are always accessible and properly embedded.

### 6. Idempotency via client_request_id
**Decision**: Every operation uses deterministic request IDs to prevent duplicate slides/decks  
**Why**: Users often retry commands when things seem slow. Idempotency ensures clean UX without creating duplicate artifacts.

## Project Constraints

### Performance  
- **Slides creation timeout**: 600 seconds max per slide (Drive upload + batchUpdate operations) - UPDATED
- **Data query timeout**: 300 seconds max (data processing + chart generation) - UPDATED  
- **LLM summarization**: 120 seconds max, with retry on validation failures  
- **Memory**: Must handle Excel files up to 50MB in memory for Parquet conversion

### API Limits
- **Vertex AI quotas**: Must respect Gemini and Imagen rate limits
- **Google Slides API**: 100 requests/100 seconds per user limit
- **Slack**: 3-second response window for slash commands (use background processing)

### Security & Compliance
- **OAuth scopes**: Minimum required permissions (Slides, Drive read/write, no admin access)
- **Data retention**: Uploaded datasets stored locally in dev, must implement proper cleanup in prod
- **Slack signature verification**: Required in production, can be bypassed locally with `DEBUG_BYPASS_SLACK_SIG=1`

### Deployment
- **Single container**: All components (FastAPI + MCP server + tools) run in one process for simplicity
- **Stateless design**: No persistent connections or in-memory state that can't be recreated
- **GCP-only**: Architecture assumes Google Cloud Platform for Vertex AI and storage services

## Current Implementation Status

### ✅ Completed (Production Ready)
- **Core PresGen**: Text reports → narrative slides with AI-generated images
- **PresGen-Data**: Excel upload → data questions → charts + insight slides  
- **Slack Integration**: Full slash command support with ephemeral responses
- **MCP Orchestration**: Robust tool chaining with timeout handling and retries
- **Smart Query Processing**: Pattern matching + LLM fallback for data questions
- **Drive Upload Pipeline**: Optimized image handling with resumable uploads

### 🚧 In Progress  
- **Production Deployment**: Moving from local uvicorn+ngrok to Cloud Run
- **Storage Migration**: Local `out/` directory → Google Cloud Storage buckets
- **Timeout Debugging**: Investigating 10-minute slides.create timeouts with enhanced GCP logging

### 📋 Planned (Next Phase)
- **PresGen-Video**: Video transcription → timed slide overlays via FFmpeg
- **Web UI**: Next.js dashboard for dataset management and presentation history

## Recent Debugging & Performance Improvements

### **Critical Fixes Applied** (January 2025)

#### 1. **Timeout Issues Resolved**
**Problem**: `slides.create` timing out after 300s, `data.query` timing out after 120s  
**Root Causes**: 
- Insufficient timeouts for complex Drive uploads (large images taking 5+ minutes)
- LLM calls to Gemini taking 10-30+ seconds for SQL generation and insights
- Broken pipe errors in MCP subprocess communication masquerading as timeouts

**Fixes Applied**:
- ✅ **Aggressive timeout increases**: `slides.create` 300s→600s, `data.query` 120s→300s
- ✅ **Enhanced MCP subprocess management**: Proper cleanup, signal handling, restart logic
- ✅ **Progress monitoring**: 30-second interval logging during long operations
- ✅ **Detailed performance profiling**: Phase-by-phase timing for data pipeline

#### 2. **Google Slides API Error Fixed**
**Problem**: `"object has no text"` errors when creating slides with empty subtitles  
**Solution**: Made subtitle element creation conditional - only create if subtitle exists and is non-empty

#### 3. **Chart Generation Enhanced**  
**Problem**: Single-value queries (e.g., "average quantity") failing to generate charts  
**Solution**: Added `single_value_bar` chart type for aggregated results

#### 4. **GCP Debug Logging Added**
**Problem**: No visibility into GCP API delays during timeout periods  
**Solution**: Comprehensive client-level logging with cost controls

**Environment Variables** (`.env`):
```bash
# Local debug logging (FREE)
ENABLE_GCP_DEBUG_LOGGING=true

# Cloud logging (COSTS MONEY - use sparingly!)  
ENABLE_CLOUD_LOGGING=true
```

### **Current Status: January 24, 2025**

#### **Environment Setup**
- **Running locally**: `uvicorn src.service.http:app --reload --port 8080`
- **GCP Debug logging**: ENABLED (both local + cloud)
- **Slack integration**: Active via ngrok tunnel
- **Recent timeout**: 10-minute `slides.create` failure with `req_id: req-a77394ce3b7cfc1b#dq1`, `gcp_trace_id: 0e1ecc46`

#### **Files Modified** (Last Session)
- `src/mcp_lab/rpc_client.py`: Enhanced timeout handling, progress logging
- `src/mcp/tools/data.py`: Performance profiling, LLM timing, chart generation fixes
- `src/agent/slides_google.py`: Conditional subtitle creation
- `src/common/jsonlog.py`: GCP debug logging with cost controls
- `.env`: Debug logging flags enabled

#### **Outstanding Issues**
- **10-minute slides.create timeouts**: Despite 600s limit, some requests still failing
- **Need log correlation**: Use `gcp_trace_id` to correlate local timeouts with GCP server-side processing
- **Drive upload bottleneck**: Likely root cause of extreme delays

#### **Next Steps for New Session**
1. **Start server**: `uvicorn src.service.http:app --reload --port 8080 2>&1 | tee -a presgen-$(date +%Y%m%d).log`
2. **Trigger timeout**: Create presentation to reproduce 10-minute failure
3. **Analyze logs**: Search for `gcp_trace_id` in both local logs and GCP Cloud Console
4. **Identify bottleneck**: Drive upload, Slides API, or Vertex AI delays
5. **Optimize**: Based on findings, implement targeted performance improvements
- **Multi-tenancy**: User isolation and workspace management
- **Cost Monitoring**: API usage tracking and budget alerts

## File Structure Philosophy

```
src/
├── agent/          # Direct Google API integrations (legacy/debugging path)
├── mcp/            # MCP server + tool implementations (primary architecture)  
├── mcp_lab/        # Orchestration and RPC client logic
├── service/        # FastAPI HTTP endpoints and Slack integration
├── common/         # Shared utilities (config, logging, caching)
└── data/           # Data ingestion and catalog management

out/                # Local development artifacts (replaced by GCS in prod)
├── data/           # Uploaded datasets as Parquet files
├── images/         # Generated charts and AI images  
└── state/          # Idempotency cache and metadata
```

**Design Principle**: Clean separation between "agent" (direct API calls for debugging) and "mcp" (production tool architecture). Both paths share common utilities but serve different purposes.

## Future Goals

### Short Term (Next 30 Days)
- **Production Infrastructure**: Deploy to Cloud Run with proper secrets management
- **Dataset Management**: Web interface for data upload, schema inspection, and query history
- **Performance Optimization**: Parallel slide creation and improved caching strategies

### Medium Term (3-6 Months)  
- **PresGen-Video MVP**: Basic video→slides overlay with transcript-based timing
- **Enterprise Features**: Team workspaces, brand templates, approval workflows
- **Integration Expansion**: Microsoft Teams, Discord, API keys for external developers

### Long Term Vision
- **Multi-Modal AI Agent**: Combine text, data, video, and voice inputs into cohesive presentations
- **Real-Time Collaboration**: Live editing and commenting on generated presentations  
- **Industry Specialization**: Vertical-specific templates and data connectors (CRM, ERP, etc.)

## Development Workflow

### Local Development
1. **Start MCP server**: `python -m src.mcp.server` (subprocess managed automatically)
2. **Start FastAPI**: `uvicorn src.service.http:app --port 8080 --reload`  
3. **Expose via ngrok**: `ngrok http 8080` → update Slack webhook URL
4. **Test via Slack**: `/presgen Make a 3-slide overview` or direct HTTP calls

### Testing Strategy
- **Unit tests**: Individual tool functions with mocked API calls
- **Integration tests**: End-to-end MCP orchestration with `RUN_SMOKE=1`
- **Live tests**: Real Slack commands against development server
- **Performance tests**: Large dataset uploads and complex multi-slide generation

### Key Environment Variables
```bash
# Required for all functionality
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1

# Slack integration  
SLACK_SIGNING_SECRET=your-slack-secret
SLACK_BOT_TOKEN=xoxb-your-bot-token

# Development only
DEBUG_BYPASS_SLACK_SIG=1  # Skip signature verification locally
```

## Common Issues & Solutions

### "Slides timeout during data questions"
- **Cause**: Large chart images taking >5 minutes to upload to Drive
- **Solution**: Implemented resumable uploads (>1MB), added detailed timing logs, retry without image on timeout
- **Monitor**: Check `drive_upload_begin/ok` logs for slow operations
- **Fallback**: If image upload times out, slides are created text-only with reduced timeout

### "MCPClient crashes with '_start' attribute error"
- **Cause**: Missing `_start()` method in MCPClient when subprocess needs restart
- **Solution**: Added proper `_start()` method that initializes subprocess and reader thread
- **Prevention**: Auto-restart on BrokenPipe now works correctly

### "Data query failures break entire request"
- **Cause**: Single failed data question would crash the whole mixed orchestration
- **Solution**: Each data query now has individual error handling with fallback responses
- **Behavior**: Failed queries create text-only slides with error messages, other queries continue

### "LLM returns wrong slide count"  
- **Cause**: Gemini interprets slide count as suggestion, not requirement
- **Solution**: Smart allocation reserves slides for data, limits narrative slides accordingly
- **Behavior**: `slides:7` with 3 data questions = 4 narrative + 3 data = 7 total max

### "Data query fails with column errors"
- **Cause**: Pattern matching selected wrong column (e.g., Date instead of Total)
- **Solution**: Enhanced column mapping with domain-specific preferences, SQL fallback on validation errors
- **Debug**: Check generated SQL in logs, verify column name matching

## Quick Reference for New Sessions

### **Start Development Server**
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Kill any existing processes
lsof -ti:8080 | xargs -r kill -9

# Start with logging
uvicorn src.service.http:app --reload --port 8080 2>&1 | tee -a presgen-$(date +%Y%m%d).log
```

### **Debug Timeout Issues**  
```bash
# Search for specific request
grep "req-ID-HERE" presgen-*.log
grep "gcp_trace_id" presgen-*.log

# Monitor GCP API calls
grep -E "(google\.api_core|googleapiclient|drive\.googleapis)" presgen-*.log
```

### **Key Files for Debugging**
- **Timeouts**: `src/mcp_lab/rpc_client.py` (METHOD_TIMEOUTS)
- **Data pipeline**: `src/mcp/tools/data.py` (timing, charts, SQL)  
- **Slides creation**: `src/agent/slides_google.py` (Drive uploads, API calls)
- **Logging setup**: `src/common/jsonlog.py` (GCP debug config)
- **Environment**: `.env` (debug flags, credentials)

### **Test Commands**
```bash
# Smoke test
RUN_SMOKE=1 python -m pytest tests/test_orchestrator_live.py -v

# Manual Slack test
curl -X POST http://localhost:8080/slack/events \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test"}'
```

### **Production Readiness Checklist**
- [ ] All timeout issues resolved and root cause identified
- [ ] GCP debug logging tested and working  
- [ ] Cloud Run deployment configuration ready
- [ ] Storage migration to GCS planned
- [ ] Cost monitoring and budget alerts configured
- [ ] Load testing with multiple concurrent users completed

---

*Last updated: January 24, 2025 - Currently debugging 10-minute slides.create timeouts*

*This document should be updated whenever architectural decisions change or new features are implemented. It serves as the single source of truth for project context and decision history.*