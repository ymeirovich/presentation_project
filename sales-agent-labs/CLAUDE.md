# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Essential Commands
- **Install dependencies**: `pip3 install -r requirements.txt`
- **Format code**: `make fmt` (uses black)
- **Lint code**: `make lint` (uses flake8)
- **Run unit tests**: `make smoke-test` (pytest on cache unit tests)
- **Run live integration tests**: `make live-smoke` (requires GCP credentials)
- **Start development server**: `uvicorn src.service.http:app --reload --port 8080`

### IMPORTANT: Python Command Usage
- **Always use `python3` instead of `python`** for all CLI commands
- **Always use `pip3` instead of `pip`** for package management
- This ensures compatibility across different system configurations

### Testing Commands
- **Individual test files**: `python3 -m pytest tests/test_orchestrator_live.py` or `python3 -m pytest tests/test_cache_unit.py`
- **With environment flag**: `RUN_SMOKE=1 python3 -m pytest tests/test_orchestrator_live.py`

### Main Entry Points
- **CLI tool**: `python3 -m src.mcp_lab examples/report_demo.txt`
- **With options**: `python3 -m src.mcp_lab examples/report_demo.txt --slides 3 --no-cache`
- **Batch processing**: `make run-batch`
- **Orchestrator demo**: `make run-orchestrator`

## Architecture Overview

This is an AI-powered presentation generation system with three main architectural layers:

### Core Architecture
1. **MCP Layer** (`src/mcp/`, `src/mcp_lab/`): JSON-RPC server handling tool orchestration
   - `src/mcp/server.py`: MCP JSON-RPC server 
   - `src/mcp/tools/`: Individual tools (llm.py, imagen.py, slides.py, data.py)
   - `src/mcp_lab/orchestrator.py`: Main orchestration logic coordinating all tools
   - `src/mcp_lab/rpc_client.py`: RPC client with timeout handling

2. **Agent Layer** (`src/agent/`): Direct Google API integrations (legacy/debug path)
   - `src/agent/llm_gemini.py`: Gemini LLM wrapper
   - `src/agent/slides_google.py`: Google Slides API integration
   - `src/agent/imagegen_vertex.py`: Vertex AI Imagen integration

3. **Service Layer** (`src/service/`): HTTP API and external integrations
   - `src/service/http.py`: FastAPI server with Slack integration

4. **Common Layer** (`src/common/`): Shared utilities
   - Config loading, structured logging, caching, retry logic, idempotency

### Key Tools (MCP-based)
- **llm.summarize**: Converts text reports into structured slide content using Gemini
- **image.generate**: Creates images from prompts using Vertex AI Imagen  
- **slides.create**: Builds Google Slides presentations with content and images
- **data.query**: Processes Excel data to generate insights and charts

## Configuration

### Required Environment Variables
```bash
# Core GCP settings
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Slack integration (optional)
SLACK_SIGNING_SECRET=your-slack-secret
SLACK_BOT_TOKEN=xoxb-your-bot-token

# Development flags
DEBUG_BYPASS_SLACK_SIG=1  # Skip Slack signature verification locally
ENABLE_GCP_DEBUG_LOGGING=true  # Enable detailed GCP API logging (free)
```

### Configuration Files
- `config.yaml`: Main configuration (models, timeouts, logging levels)
- `oauth_slides_client.json`: OAuth credentials for Google Slides access
- `.env`: Environment variables (not in repo)

## Development Workflow

### Starting Development
1. **Start MCP server**: Automatically managed by orchestrator
2. **Start FastAPI server**: `uvicorn src.service.http:app --port 8080 --reload`
3. **For Slack integration**: Use ngrok to expose local server
4. **Test**: Via Slack commands or direct HTTP calls

### Authentication Setup
- **Service Account**: For Vertex AI and Drive API (set via GOOGLE_APPLICATION_CREDENTIALS)
- **OAuth**: For Google Slides API (run: `python -c "from src.agent.slides_google import authenticate; authenticate()"`)

### Key Files to Understand
- **Timeout configuration**: `src/mcp_lab/rpc_client.py` (METHOD_TIMEOUTS)
- **Main orchestration**: `src/mcp_lab/orchestrator.py` 
- **Data processing pipeline**: `src/mcp/tools/data.py`
- **Slides creation**: `src/agent/slides_google.py`
- **Logging setup**: `src/common/jsonlog.py`

## Important Implementation Details

### Timeout Handling
The system has aggressive timeouts due to GCP API latency:
- `slides.create`: 600 seconds (Drive upload bottleneck)
- `data.query`: 300 seconds (complex data processing)
- `llm.summarize`: 120 seconds (LLM calls)

### Idempotency
All operations use deterministic `client_request_id` to prevent duplicates. State stored in `out/state/idempotency.json`.

### Caching Strategy
- LLM responses cached by content hash (`out/state/cache/llm_summarize/`)
- Generated images cached by prompt hash (`out/state/cache/imagen/`)
- Cache TTL configurable via `--cache-ttl-hours`

### Error Recovery
- Individual tool failures don't crash entire pipeline
- Retry logic with exponential backoff for transient failures
- Fallback text-only slides when image generation fails

## Output Structure
```
out/
├── data/              # Uploaded datasets as Parquet files  
├── images/            # Generated charts and AI images
│   └── charts/        # Data visualizations
└── state/             # Idempotency and caching
    ├── cache/         # Tool result caches
    ├── idempotency.json
    └── datasets.json  # Data catalog
```

## Debugging Common Issues

### Performance Issues
- Enable GCP debug logging: `ENABLE_GCP_DEBUG_LOGGING=true`
- Check timeout logs in `src/mcp_lab/rpc_client.py`
- Monitor Drive upload timing in logs

### Authentication Failures
- Verify service account permissions (Vertex AI User, Storage Admin)
- Check OAuth token validity for Slides API
- Ensure all required APIs enabled in Google Cloud

### Data Processing Errors
- Check column name matching in SQL generation
- Verify Parquet file creation from Excel uploads
- Review pattern matching vs LLM fallback in `src/mcp/tools/data.py`

## Testing Strategy

### Unit Tests (Fast)
- Cache functionality: `tests/test_cache_unit.py`
- No external API dependencies

### Integration Tests (Requires GCP)
- Full orchestration: `tests/test_orchestrator_live.py` 
- Batch processing: `tests/test_batch_live.py`
- Set `RUN_SMOKE=1` environment variable

### Live Testing
- Use real Slack commands against development server
- Test with various data file formats and sizes
- Verify end-to-end presentation generation