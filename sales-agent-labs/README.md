# AI Agent: Automated Slide Deck Creation

A production-ready AI Agent that automates slide deck creation from text reports by summarizing content, generating images, and building Google Slides presentations.

## 🔮 What This Agent Does

This AI Agent transforms raw text reports into polished Google Slides presentations by:

- **Summarizing reports** into slide-ready titles, bullets, speaker notes, and image prompts (via Gemini 2.0 Flash)
- **Generating visuals** from structured prompts (via Vertex Imagen)
- **Building Google Slides decks** programmatically with content + images
- **Running through an orchestrator** (MCP-based JSON-RPC server) with validation, retries, idempotency, and logging
- **Integrating externally** via HTTP/Slack shims with batching, caching, and quota guardrails

## 🏗️ Architecture Overview

### MCP Layer (`src/mcp/`, `src/mcp_lab/`)
- Handles JSON-RPC requests, schemas, tool exposure, and orchestrator logic
- Three core tools: `llm.summarize`, `image.generate`, `slides.create`

### Agent Layer (`src/agent/`)
- Legacy/debug path with reusable modules for LLM calls, image generation, slides, validation

### Common Layer (`src/common/`)
- Shared utilities (config, logging, idempotency, retries)

### Tests (`tests/`, `test/`)
- Smoke + live tests for end-to-end validation

### Outputs (`out/`)
- Slide payloads, generated images, state cache for idempotency

## 🚀 Features

- **Multi-Model Integration**: Gemini 2.0 Flash for summarization, Vertex Imagen for image generation
- **Google Slides API**: Programmatic slide creation with images, text, and formatting
- **Robust Error Handling**: Retry logic with exponential backoff, comprehensive logging
- **Caching & Idempotency**: Prevents duplicate work, enables resumable operations
- **Batch Processing**: Handle multiple reports efficiently
- **Configurable**: Flexible configuration via YAML and environment variables

## 📋 Prerequisites

- Python 3.8+
- Google Cloud Project with enabled APIs:
  - Vertex AI API
  - Google Slides API
  - Google Drive API
- Service Account with appropriate permissions
- OAuth credentials for Google Slides access

## 🛠️ Installation & Setup

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd sales-agent-labs
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file with the following variables:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_REGION=us-central1

# Authentication
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Optional: Custom model configurations
GEMINI_MODEL=gemini-2.0-flash-001
IMAGEN_MODEL=imagegeneration@006
```

### 3. Authentication Setup

#### Service Account (for Vertex AI)
1. Create a service account in Google Cloud Console
2. Grant roles: `Vertex AI User`, `Storage Admin`
3. Download JSON key file
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to the file path

#### OAuth (for Google Slides)
1. Create OAuth 2.0 credentials in Google Cloud Console
2. Download `oauth_slides_client.json`
3. Run initial authentication:
```bash
python -c "from src.agent.slides_google import authenticate; authenticate()"
```

### 4. Configuration

Edit `config.yaml` to customize:

```yaml
project:
  id: ${GOOGLE_PROJECT_ID}
  region: ${GOOGLE_CLOUD_REGION}

llm:
  provider: gemini
  model: gemini-2.0-flash-001
  max_output_tokens: 8192
  temperature: 0.2

imagen:
  provider: vertex
  model: imagegeneration@006
  size: "1280x720"
  share_image_public: true

slides:
  default_title: "AI Generated Presentation"
  share_image_public: true
  aspect: "16:9"

logging:
  level: INFO
```

## 🎯 Usage

### Basic Usage

Generate a slide deck from a text report:

```bash
python -m src.mcp_lab examples/report_demo.txt
```

### Advanced Options

```bash
# Generate multiple slides
python -m src.mcp_lab examples/report_demo.txt --slides 3

# Custom request ID for idempotency
python -m src.mcp_lab examples/report_demo.txt --request-id my-unique-id

# Disable caching
python -m src.mcp_lab examples/report_demo.txt --no-cache

# Custom cache TTL
python -m src.mcp_lab examples/report_demo.txt --cache-ttl-hours 2.0
```

### Batch Processing

Process multiple reports:

```bash
make run-batch
```

### Development Commands

```bash
# Run smoke tests
make smoke-test

# Run live end-to-end tests
make live-smoke

# Format code
make fmt

# Lint code
make lint

# Run orchestrator with demo
make run-orchestrator
```

## 📁 Project Structure

```
sales-agent-labs/
├── src/
│   ├── agent/              # Legacy agent modules
│   │   ├── llm_gemini.py   # Gemini LLM wrapper
│   │   ├── slides_google.py # Google Slides API
│   │   ├── imagegen_vertex.py # Vertex Imagen
│   │   └── ...
│   ├── mcp/                # MCP server & tools
│   │   ├── server.py       # JSON-RPC server
│   │   ├── schemas.py      # Tool schemas
│   │   └── tools/          # Individual tools
│   │       ├── llm.py      # llm.summarize tool
│   │       ├── imagen.py   # image.generate tool
│   │       └── slides.py   # slides.create tool
│   ├── mcp_lab/            # Orchestrator
│   │   ├── orchestrator.py # Main orchestration logic
│   │   ├── rpc_client.py   # MCP client
│   │   └── __main__.py     # CLI entry point
│   └── common/             # Shared utilities
│       ├── config.py       # Configuration loader
│       ├── jsonlog.py      # Structured logging
│       ├── cache.py        # Caching utilities
│       └── backoff.py      # Retry logic
├── tests/                  # Test suites
├── examples/               # Sample reports
├── out/                    # Generated outputs
├── config.yaml             # Main configuration
├── requirements.txt        # Python dependencies
└── Makefile               # Development commands
```

## 🔧 Core Components

### Tools

1. **`llm.summarize`**: Converts text reports into structured slide content
2. **`image.generate`**: Creates images from text prompts using Vertex Imagen
3. **`slides.create`**: Builds Google Slides presentations with content and images

### Orchestrator

The orchestrator (`src/mcp_lab/orchestrator.py`) coordinates the entire pipeline:

1. Summarizes input text into slide sections
2. Generates images for each section (best effort)
3. Creates Google Slides presentation with content and images
4. Handles caching, retries, and error recovery

### Key Features

- **Idempotency**: Same input produces same output, prevents duplicate work
- **Caching**: Stores LLM and image generation results to avoid redundant API calls
- **Retry Logic**: Exponential backoff for transient failures
- **Structured Logging**: JSON logs with request IDs for debugging
- **Schema Validation**: Ensures data integrity throughout the pipeline

## 🧪 Testing

### Smoke Tests
```bash
make smoke-test
```

### Live End-to-End Tests
```bash
make live-smoke
```

### Individual Tool Tests
```bash
python -m pytest tests/test_orchestrator_live.py
python -m pytest tests/test_cache_unit.py
```
## Debugging with debugpy
```bash
DEBUGPY=1 DEBUGPY_WAIT=1 python3 -m src.mcp_lab ./examples/report_demo.txt --slides 3 --no-cache
```
## 🐛 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify service account permissions
   - Check OAuth token validity
   - Ensure APIs are enabled in Google Cloud

2. **Image Generation Failures**
   - Check Vertex AI quotas
   - Verify region availability
   - Review safety filter settings

3. **Slides Creation Issues**
   - Confirm Google Slides API access
   - Check Drive permissions for image uploads
   - Verify presentation sharing settings

### Debug Logging

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
python -m src.mcp_lab examples/report_demo.txt
```

### Known Limitations

- Image generation may fail for certain prompts due to safety filters
- Local file URLs cannot be directly used in Google Slides (requires Drive upload)
- LLM may occasionally generate fewer bullet points than requested

## 🔄 Development Workflow

1. **Code Formatting**: `make fmt`
2. **Linting**: `make lint`
3. **Testing**: `make smoke-test`
4. **Live Testing**: `make live-smoke`

### Adding New Features

1. Implement in appropriate layer (`agent/`, `mcp/`, `common/`)
2. Add tests in `tests/`
3. Update configuration if needed
4. Run full test suite

## 📊 Monitoring & Observability

The agent includes comprehensive logging:

- **Request Tracking**: Unique request IDs for tracing
- **Performance Metrics**: Timing and success rates
- **Error Reporting**: Detailed error context
- **Cache Statistics**: Hit/miss rates and storage usage

Logs are structured JSON for easy parsing and analysis.

## 🚀 Production Deployment

For production use:

1. **Environment**: Use production Google Cloud project
2. **Scaling**: Consider batch processing for high volume
3. **Monitoring**: Set up log aggregation and alerting
4. **Security**: Rotate credentials regularly, use IAM best practices
5. **Quotas**: Monitor API usage and set appropriate limits

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `make fmt lint smoke-test`
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🤝 Support

For issues and questions:
- Check the troubleshooting section
- Review logs with DEBUG level enabled
- Open an issue with reproduction steps

---

**Built with ❤️ using Google Cloud AI, MCP, and modern Python practices.**
