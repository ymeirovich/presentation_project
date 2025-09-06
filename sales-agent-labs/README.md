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

### Core Presentation Generation
- **Multi-Model Integration**: Gemini 2.0 Flash for summarization, Vertex Imagen for image generation
- **Google Slides API**: Programmatic slide creation with images, text, and formatting
- **Smart Image Handling**: Automatic base64 encoding for small images, Drive upload for larger files
- **Speaker Notes Integration**: Multiple fallback strategies for reliable speaker notes insertion

### Data-Driven Presentations with RAG
- **Excel/CSV Processing**: Upload spreadsheet data and generate insights with charts and visualizations
- **RAG Context Integration**: Combine report text or uploaded documents with data analysis
- **Multi-line Question Input**: Support for up to 20 analysis questions with intelligent parsing
- **Interactive Controls**: Slide count (3-20), chart styles (Modern/Classic/Minimal), template styles (Corporate/Creative/Minimal)
- **AI-Enhanced Insights**: Include AI images and speaker notes with customizable presentation titles

### Modern Web Interface
- **Next.js Frontend**: Modern React interface with dark theme and responsive design
- **Drag-and-Drop Uploads**: Intuitive file handling for data (.xlsx/.csv) and reports (.txt)
- **Real-time Status**: Live updates with loading states, progress indicators, and clickable result links
- **Centered Navigation**: Professional tabbed interface (PresGen-Core, PresGen-Data, PresGen-Video)
- **Comprehensive Validation**: Form validation with helpful error messages and user guidance

### System Integration & Reliability
- **HTTP/Slack Integration**: REST API and Slack bot commands for external integrations  
- **Enhanced Error Handling**: Comprehensive error tracking, retry logic with exponential backoff, bytes object detection
- **Caching & Idempotency**: Prevents duplicate work, enables resumable operations with file-backed persistence
- **Batch Processing**: Handle multiple reports efficiently with queue management
- **Production Logging**: Structured JSON logging with request tracing and performance metrics
- **Configurable**: Flexible configuration via YAML and environment variables

## 🎯 Current Status

### ✅ **Production Ready System**
The PresGen MVP is now a **fully functional, production-ready system** with:

- **🖥️ Complete Web Interface**: Modern Next.js frontend at http://localhost:3003
- **⚙️ Stable Backend API**: FastAPI server with comprehensive error handling
- **📊 Data Processing Pipeline**: Excel/CSV upload → analysis → chart generation → slide creation
- **🤖 AI Integration**: Gemini 2.0 Flash + Vertex Imagen working seamlessly
- **📑 Google Slides Integration**: Automated presentation creation with images and speaker notes
- **🔄 End-to-End Workflows**: Text-based and data-driven presentation generation

### 🎨 **User Experience Features**
- **Intuitive Interface**: Dark theme, responsive design, professional styling
- **Smart Validation**: Real-time form validation with helpful error messages
- **File Handling**: Drag-and-drop uploads with progress indicators and error handling
- **Success Feedback**: Clickable "Open Slides" buttons instead of raw JSON responses
- **Loading States**: Clear progress indicators during processing

### 🛠️ **Technical Achievements**
- **Error Resolution**: Fixed critical HTTP 500 JSON serialization errors
- **RAG Integration**: Intelligent context combination for enhanced data insights  
- **Multi-format Support**: Text reports, Excel/CSV data, with extensible architecture
- **Comprehensive Logging**: Full request tracing with structured JSON logs
- **Security**: Input validation, file type restrictions, size limits

### 🎬 **PresGen-Video: Complete Video Processing Pipeline**
**Video → Professional Presentation** workflow with full-screen architecture:

#### **🏆 Production-Ready Features**
- **📽️ Full-Screen Video Composition**: Advanced FFmpeg-based video processing with right-side highlight overlays
- **🎯 Smart Timeline Correction**: Automatic timestamp redistribution to fit actual video duration (1:06)
- **📝 Subtitle Generation**: SRT file creation for debugging and external use
- **⚡ Real-Time Processing**: Phase 3 composition with drawtext filters and professional styling
- **🔧 Context7 Integration**: Live API documentation for video processing tools

#### **🏗️ Complete Architecture (All Phases)**
- **Phase 1**: Parallel audio extraction + face detection (4.56s, 85% faster than target)
- **Phase 2**: Content analysis + slide generation with AI-powered transcription  
- **Phase 3**: ✅ **NEW** Full-screen video composition with timed bullet overlays
- **Phase 4**: User preview interface with corrected timestamps and proper video duration
- **Phase 5**: Final video download with professional presentation formatting

#### **🎨 Advanced Video Features**
- **Smart Text Overlays**: Right-side rectangle (320px) with numbered bullet points
- **Professional Typography**: Navy blue text, 20px font, word wrapping within bounds
- **Intelligent Spacing**: 20px margin-bottom between bullets with progressive positioning
- **Duration-Aware Processing**: Automatic detection of 66-second video length via ffprobe
- **Timeline Synchronization**: Bullets timed at 0s, 12s, 24s, 36s, 48s with proper spacing

#### **📋 Status: Module 3 Complete! 🎉**
- **⏱️ Progress**: 3/5 modules complete (60% complete)
- **🚀 Performance**: Sub-5-second Phase 1, optimized Phase 3 composition
- **💰 Cost**: $0 processing cost with local-first architecture
- **🎯 Next**: Module 4 (UI refinements) and Module 5 (final optimizations)

[📖 View Video Implementation Plan](presgen-video/Implementation-Status.md) | [📑 Technical PRDs](presgen-video/)

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

### Web UI (Recommended)

1. **Start the backend server:**
```bash
uvicorn src.service.http:app --reload --port 8080
```

2. **Start the frontend (in a new terminal):**
```bash
cd presgen-ui
npm install
npm run dev
```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8080
   - Optional: Use ngrok for external access

### Basic CLI Usage

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
│   │       ├── slides.py   # slides.create tool
│   │       ├── data.py     # data.query tool
│   │       ├── video_audio.py    # video.audio tool
│   │       ├── video_face.py     # video.face tool
│   │       ├── video_content.py  # video.content tool
│   │       ├── video_slides.py   # video.slides tool
│   │       ├── video_phase3.py   # video.phase3 tool
│   │       ├── video_orchestrator.py # Parallel processing
│   │       └── context7.py # context7 tool
│   ├── mcp_lab/            # Orchestrator
│   │   ├── orchestrator.py # Main orchestration logic
│   │   ├── rpc_client.py   # MCP client
│   │   └── __main__.py     # CLI entry point
│   ├── service/            # HTTP API & integrations
│   │   └── http.py         # FastAPI server with video endpoints
│   └── common/             # Shared utilities
│       ├── config.py       # Configuration loader
│       ├── jsonlog.py      # Structured logging
│       ├── cache.py        # Caching utilities
│       └── backoff.py      # Retry logic
├── presgen-video/          # Video processing documentation
│   ├── Implementation-Status.md # Current progress
│   ├── PresgenVideoPRD.md  # Product requirements
│   ├── subtitles/          # Generated SRT files
│   ├── srt/               # Legacy subtitle files  
│   └── logs/              # Processing logs
├── presgen-ui/            # Next.js frontend
│   ├── pages/             # React components
│   ├── styles/            # CSS styling
│   └── package.json       # Frontend dependencies
├── tests/                 # Test suites
├── examples/              # Sample reports
├── out/                   # Generated outputs
├── /tmp/jobs/             # Video processing workspace
├── config.yaml            # Main configuration
├── requirements.txt       # Python dependencies
└── Makefile              # Development commands
```

## 🔧 Core Components

### Tools

#### Core Presentation Tools
1. **`llm.summarize`**: Converts text reports into structured slide content
2. **`image.generate`**: Creates images from text prompts using Vertex Imagen
3. **`slides.create`**: Builds Google Slides presentations with content and images
4. **`data.query`**: Processes Excel/CSV data to generate insights and charts

#### Video Processing Tools
5. **`video.audio`**: Extracts and segments audio from video files using Context7-optimized ffmpeg
6. **`video.face`**: Detects faces and calculates stable crop regions using OpenCV  
7. **`video.content`**: Analyzes video content and generates slide summaries with AI transcription
8. **`video.slides`**: Creates slide images from content summaries with professional styling
9. **`video.phase3`**: Orchestrates full-screen video composition with timed bullet overlays
10. **`context7`**: Provides real-time API documentation for video processing libraries

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

### Unit Tests (Smoke Tests)
```bash
make smoke-test
```
This runs the unit tests, which do not require any external APIs.

### Live End-to-End Tests
```bash
make live-smoke
```
This runs the live end-to-end tests, which require a connection to Google Cloud services.

### Individual Tool Tests
```bash
python -m pytest tests/test_orchestrator_live.py
python -m pytest tests/test_cache_unit.py
```

## Recent Changes

### Complete System Integration & UI Enhancement (Latest)
- **✅ Fixed HTTP 500 Error**: Resolved "Object of type bytes is not JSON serializable" error that was preventing presentation generation
- **✅ Enhanced Error Logging**: Added comprehensive error tracking throughout the pipeline with stack traces and context
- **✅ Improved JSON Serialization**: Added SafeJSONEncoder to handle bytes objects and complex data types safely
- **✅ Server Card Hyperlinks**: Successfully generated presentations now display as clickable "Open Slides" buttons instead of raw JSON

### PresGen-Data RAG Upgrade (Latest)
- **✅ RAG Context Integration**: Added Report Text textarea OR Report File upload (.txt files) with intelligent priority handling
- **✅ Multi-line Questions**: Enhanced question input with textarea supporting up to 20 questions (one per line)
- **✅ Required Presentation Title**: Added mandatory title field with validation (minimum 3 characters)
- **✅ Enhanced Controls**: Added Include AI Images, Speaker Notes toggles, and Template Style selector
- **✅ Slide Count Control**: Interactive slider from 3-20 slides with visual feedback
- **✅ Chart Style Options**: Modern/Classic/Minimal chart styling options
- **✅ Centered Navigation**: Improved header layout with properly centered tab navigation
- **✅ Comprehensive Validation**: Full form validation with user-friendly error messages and loading states

### Previous Improvements
- **Bug Fixes**: Addressed several bugs, including a circular import, an `AttributeError` in the MCP client, a `SyntaxError` in the HTTP service, and an `UnboundLocalError` in the orchestrator.
- **Refactoring**: Improved the structure and readability of the HTTP service and the orchestrator.
- **Testing**: Updated the testing framework, removed the old smoke tests, and streamlined the test commands in the `Makefile`.
- **Data Pipeline**: Added Excel/CSV data processing with chart generation and data-driven slide creation
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
- ~~Local file URLs cannot be directly used in Google Slides (requires Drive upload)~~ ✅ **Fixed**: Added automatic Drive upload for local images
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
