# CLAUDE.md - AI Assistant Guide

This document provides comprehensive guidance for AI assistants working on the PaddleOCR PDF to Markdown conversion project.

## Project Overview

**Purpose**: A client-server application for converting PDF files to Markdown format using PaddleOCR's PP-StructureV2 document parsing pipeline.

**Technology Stack**:
- **Server**: Python 3.10, Flask, PaddleOCR 2.8.1, PaddlePaddle GPU 2.5.2
- **Client**: Python 3.10, requests library
- **Deployment**: RunPod GPU instances (typically RTX 3090 or better)

**Key Features**:
- REST API-based PDF submission and retrieval
- Job queueing system with status tracking
- Batch processing support
- GPU acceleration for 30-40x faster processing
- Multi-language OCR support (100+ languages)

## Architecture

### High-Level Flow

```
┌─────────────────┐           ┌──────────────────────────────────┐
│                 │           │          Server                   │
│  Client         │           │  ┌────────────────────────────┐  │
│  (client.py)    │  HTTP     │  │  Flask API (server.py)     │  │
│                 │  ─────────┼─▶│  - /submit  - /status      │  │
│  - Scans PDFs   │           │  │  - /result  - /health      │  │
│  - Uploads      │           │  └────────────────────────────┘  │
│  - Polls status │           │              │                    │
│  - Saves .md    │           │              ▼                    │
│                 │           │  ┌────────────────────────────┐  │
└─────────────────┘           │  │  Queue Manager             │  │
                              │  │  (queue_manager.py)        │  │
                              │  │  - Job queue (FIFO)        │  │
                              │  │  - Worker threads          │  │
                              │  │  - Status tracking         │  │
                              │  └────────────────────────────┘  │
                              │              │                    │
                              │              ▼                    │
                              │  ┌────────────────────────────┐  │
                              │  │  PDF Processor             │  │
                              │  │  (pdf_processor.py)        │  │
                              │  │  - PaddleOCR integration   │  │
                              │  │  - PDF → Markdown          │  │
                              │  └────────────────────────────┘  │
                              └──────────────────────────────────┘
```

### Component Breakdown

#### 1. Server Components

**`server/server.py`** (343 lines)
- Flask REST API server
- Endpoints: `/health`, `/submit`, `/status/{job_id}`, `/result/{job_id}`, `/stats`, `/batch/status`
- Configuration loading from `config.json`
- CRITICAL: Sets up CUDA/CUDNN library paths before PaddleOCR imports (lines 16-36)
- Initializes PDFProcessor and QueueManager
- Max file size: 500MB

**`server/queue_manager.py`** (256 lines)
- Job queue management using Python's `queue.Queue`
- Worker thread pool for processing jobs
- Job lifecycle: QUEUED → PROCESSING → COMPLETED/FAILED
- In-memory storage (jobs lost on restart)
- Thread-safe operations with locks
- Key class: `QueueManager` with methods: `submit_job()`, `get_job_status()`, `get_job_result()`

**`server/pdf_processor.py`** (192 lines)
- PaddleOCR PPStructure integration
- Uses PPStructure (not PPStructureV3) with PaddleOCR 2.8.1
- Processes PDF bytes → Markdown text
- Handles text, tables, and figures/images
- Creates temporary files for processing
- Key class: `PDFProcessor` with method: `process_pdf(pdf_data, output_dir)`

#### 2. Client Components

**`client/client.py`** (551 lines)
- CLI tool for PDF conversion
- Directory scanning (recursive/non-recursive)
- Parallel uploads using ThreadPoolExecutor
- Status polling with configurable intervals
- Progress tracking and statistics
- Two output modes: quiet (default) and verbose
- Key class: `PDFConverterClient`
- Features:
  - Health checks before processing
  - Auto-skip already converted PDFs
  - Dynamic timeouts based on file size
  - Batch processing support

#### 3. Configuration Files

**`server/config.json`**
```json
{
  "host": "0.0.0.0",
  "port": 5000,
  "num_workers": 1,
  "use_gpu": false,
  "lang": "en",
  "debug": false
}
```

**`client/config.json`**
```json
{
  "server_url": "http://localhost:5000",
  "poll_interval": 2.0,
  "timeout": 300,
  "workers": 2
}
```

## Codebase Structure

```
PaddleOCR_PDF2Markdown/
├── server/                          # Server application
│   ├── server.py                    # Flask REST API
│   ├── queue_manager.py             # Job queue & workers
│   ├── pdf_processor.py             # PaddleOCR integration
│   ├── config.json                  # Server config
│   ├── requirements.txt             # Python dependencies
│   ├── test_gpu.py                  # GPU testing utility
│   ├── setup_gpu.sh                 # GPU setup script
│   ├── start_server.sh              # Server startup script
│   ├── README.md                    # Server documentation
│   ├── DEPLOYMENT_INSTRUCTIONS.md   # Deployment guide
│   └── CLIENT_TIMEOUT_CONFIG.md     # Timeout configuration docs
│
├── client/                          # Client application
│   ├── client.py                    # CLI client
│   ├── config.json                  # Client config
│   ├── config.example.json          # Config template
│   └── requirements.txt             # Python dependencies
│
├── server_verified/                 # Verified working backup
│   └── [mirror of server/]          # Known-good server files
│
├── .claude/                         # Claude Code configuration
│   └── settings.local.json          # Local settings
│
├── deploy_to_runpod.bat            # Windows deployment script
├── deploy_to_runpod.sh             # Linux/Mac deployment script
├── README.md                        # Main project documentation
├── QUICK_START.md                   # Quick start guide
├── RUNPOD_DEPLOYMENT.md            # RunPod deployment guide
├── .gitignore                       # Git ignore rules
└── CLAUDE.md                        # This file
```

## Key Conventions & Patterns

### 1. Code Style

- **Python Version**: 3.10 (3.11 supported but 3.10 recommended)
- **Docstrings**: Google-style docstrings for all classes and functions
- **Logging**: Use `logging` module, not print statements (except client output)
- **Error Handling**: Try-except blocks with specific exception types
- **Type Hints**: Use typing module for function signatures (Optional, Dict, List, Tuple)

### 2. API Design

- **RESTful endpoints**: Standard HTTP methods (GET, POST)
- **JSON responses**: All API responses return JSON
- **Status codes**:
  - 200: Success
  - 202: Accepted (job processing)
  - 400: Bad request
  - 404: Not found
  - 413: File too large
  - 500: Internal error

### 3. Job Processing

- **Job ID**: UUID v4 strings
- **Status flow**: QUEUED → PROCESSING → COMPLETED/FAILED
- **Timestamps**: ISO format datetime strings
- **Thread safety**: All shared state protected by locks

### 4. File Handling

- **Temporary files**: Created for PDF processing, cleaned up in finally block
- **Secure filenames**: Use `werkzeug.utils.secure_filename()`
- **Path handling**: Use `pathlib.Path` for cross-platform compatibility

## Critical Dependencies

### Server Dependencies (server/requirements.txt)

**CRITICAL VERSION CONSTRAINTS**:
```
paddleocr==2.8.1               # MUST be 2.8.1, uses PPStructure
paddlepaddle-gpu==2.5.2        # MUST be 2.5.2 for compatibility
numpy<2.0                      # MUST be <2.0 for PaddleOCR 2.8.1 compatibility
```

**Other Key Dependencies**:
- flask>=3.0.0
- opencv-python>=4.6.0
- Pillow>=10.0.0
- requests>=2.31.0

### Client Dependencies (client/requirements.txt)

```
requests>=2.31.0
tqdm>=4.66.0
```

### CUDA/GPU Setup

**Environment Variables** (set in server.py lines 16-36):
```python
LD_LIBRARY_PATH includes:
- /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib
- /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib
- ... (7 NVIDIA library paths total)

FLAGS_fraction_of_gpu_memory_to_use=0.8
FLAGS_gpu_memory_growth=1
CUDA_VISIBLE_DEVICES=0
```

## Development Workflows

### 1. Adding New Server Endpoints

1. Add route handler in `server/server.py`
2. Use appropriate HTTP method decorator (@app.route)
3. Validate request data
4. Call queue_manager or pdf_processor methods
5. Return JSON response with proper status code
6. Add error handling with try-except
7. Update API documentation in README.md

### 2. Modifying PDF Processing

1. Edit `server/pdf_processor.py`
2. Test with `python pdf_processor.py test.pdf` (standalone mode)
3. Check for memory leaks (temporary file cleanup)
4. Verify GPU/CPU compatibility
5. Update markdown conversion logic in `process_pdf()` method

### 3. Client Feature Addition

1. Edit `client/client.py`
2. Add CLI argument parsing in `parse_arguments()`
3. Implement feature in `PDFConverterClient` class
4. Update help text in `main()`
5. Test with various scenarios (single file, batch, recursive)

### 4. Configuration Changes

1. Update default configs in load_config() functions
2. Update example config files
3. Document new options in README.md
4. Ensure backward compatibility with old configs

## Common Tasks for AI Assistants

### 1. Debugging Server Issues

**Check logs**:
- Server uses Python logging module
- Logs show: initialization, job submission, processing, completion
- Look for ERROR level messages

**Common issues**:
- CUDA library not found → Check LD_LIBRARY_PATH setup in server.py:18-31
- PaddleOCR import error → Check version compatibility (2.8.1 required)
- GPU not detected → Run `server/test_gpu.py`
- Port already in use → Change port in `server/config.json`

### 2. Debugging Client Issues

**Check health endpoint first**:
```bash
curl http://server:port/health
```

**Common issues**:
- Connection refused → Server not running or wrong URL
- Timeout → Increase `timeout` in client/config.json
- Upload fails → Check file size (500MB limit)
- Wrong server URL → Verify config.json or --server flag

### 3. Testing Changes

**Server testing**:
```bash
cd server
python server.py  # Start server

# In another terminal:
cd client
python client.py test.pdf
```

**Standalone PDF processor test**:
```bash
cd server
python pdf_processor.py input.pdf  # Creates input.md
```

**GPU test**:
```bash
cd server
python test_gpu.py
```

### 4. Deployment to RunPod

**Process**:
1. Use `deploy_to_runpod.sh` or `.bat` script
2. SSH into RunPod instance
3. Navigate to `/workspace/pdf2markdown`
4. Start server: `python server.py` or use screen
5. Get public URL from RunPod dashboard (port 7777 or 5000)
6. Update `client/config.json` with server URL
7. Test with health check

**Key files**:
- `RUNPOD_DEPLOYMENT.md`: Full deployment guide
- `QUICK_START.md`: Quick reference
- `server/setup_gpu.sh`: GPU environment setup
- `server/start_server.sh`: Server startup automation

## Important Notes for AI Assistants

### 1. Version Constraints

**NEVER upgrade these without testing**:
- PaddleOCR must be 2.8.1 (not 2.9.x or 3.x)
- PaddlePaddle must be 2.5.2 (not 3.x)
- NumPy must be <2.0 (not 2.x)

These versions are locked for compatibility. The codebase uses PPStructure from PaddleOCR 2.8.1, which has different APIs than newer versions.

### 2. Server Startup Sequence

**Critical order** (see server.py:16-42):
1. Set LD_LIBRARY_PATH for CUDA libraries FIRST
2. Set PaddlePaddle environment variables
3. THEN import Flask
4. THEN import pdf_processor (which imports PaddleOCR)

Do not reorder these imports!

### 3. Thread Safety

- `QueueManager.jobs` dict is shared across threads
- Always acquire `self.lock` before accessing jobs
- Job queue is thread-safe by design (queue.Queue)
- Worker threads use daemon=True (killed when main exits)

### 4. Memory Management

- PDF data is kept in memory during processing
- Temporary files are created and MUST be cleaned up
- Use try-finally blocks for cleanup
- Large PDFs (>100MB) may cause memory pressure

### 5. Client Behavior

- Client polls server every `poll_interval` seconds (default: 2.0)
- Timeout is total wait time, not per-request timeout
- Upload timeout is dynamic: 60s + (15s per MB)
- Already-converted PDFs are skipped (checks for .md file)

### 6. RunPod Specifics

- Default ports: 5000 (config) or 7777 (common usage)
- RunPod exposes ports via HTTPS proxy URLs
- Server binds to 0.0.0.0 for external access
- GPU is assumed available when `use_gpu: true`
- Persistent storage: `/workspace/`

### 7. Error Messages

**Server errors include**:
- Job ID in all log messages for traceability
- Exception details in job.error field
- Separate logging for submit, process, complete stages

**Client errors include**:
- Filename in error messages
- Statistics tracking for failed conversions
- Quiet mode shows only errors, verbose shows all

## Testing Checklist

Before committing changes:

- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] Single PDF conversion works
- [ ] Batch processing works
- [ ] Status endpoint returns correct states
- [ ] Result endpoint returns markdown
- [ ] Client can upload files
- [ ] Client handles errors gracefully
- [ ] GPU detection works (if applicable)
- [ ] Temporary files are cleaned up
- [ ] No new dependencies without justification
- [ ] Documentation updated if behavior changed

## Git Workflow

- **Main branch**: Development happens on feature branches
- **Branch naming**: `claude/claude-md-{session-id}`
- **Commits**: Clear, descriptive commit messages
- **Push**: Use `git push -u origin branch-name`
- **Backup**: `server_verified/` contains known-good server files

## Environment Setup

### Server Setup
```bash
cd server
pip install -r requirements.txt
python server.py
```

### Client Setup
```bash
cd client
pip install -r requirements.txt
python client.py -h  # Show help
```

### GPU Setup (RunPod)
```bash
cd server
bash setup_gpu.sh
python test_gpu.py  # Verify GPU
```

## Performance Characteristics

### CPU Mode
- ~3-4 seconds per page
- 2-4GB RAM usage
- 100-page PDF: ~5-7 minutes
- Suitable for: development, small batches

### GPU Mode (RTX 3090)
- ~100ms per page (30-40x faster)
- 1-2GB VRAM usage
- 100-page PDF: ~10 seconds
- Suitable for: production, large batches

## API Reference Quick Guide

### POST /submit
- **Input**: multipart/form-data with 'file' or 'files[]'
- **Returns**: `{job_id, filename, status: "queued"}`
- **Max size**: 500MB

### GET /status/{job_id}
- **Returns**: `{job_id, filename, status, created_at, started_at, completed_at, error}`
- **Status values**: "queued", "processing", "completed", "failed"

### GET /result/{job_id}
- **Returns**: `{job_id, filename, markdown, image_count, completed_at}`
- **Status 202**: If still processing
- **Status 404**: If job not found

### GET /health
- **Returns**: `{status: "healthy", service, version}`
- **Use for**: Server availability checks

### GET /stats
- **Returns**: `{queue_size, total_jobs, queued, processing, completed, failed}`
- **Use for**: Monitoring and debugging

## Troubleshooting Guide

### Server won't start
1. Check Python version: `python --version` (should be 3.10 or 3.11)
2. Check dependencies: `pip list | grep paddle`
3. Check port availability: `netstat -tulpn | grep 5000`
4. Check logs for import errors

### GPU not working
1. Run `python test_gpu.py`
2. Check CUDA: `nvidia-smi`
3. Verify PaddlePaddle GPU: `python -c "import paddle; print(paddle.is_compiled_with_cuda())"`
4. Check LD_LIBRARY_PATH in server.py

### Client timeouts
1. Increase `timeout` in client/config.json
2. Check network connectivity to server
3. Verify server is processing (check logs)
4. For large files, expect longer processing times

### Poor OCR quality
1. Check PDF quality (scanned vs. native)
2. Try different `lang` setting in server/config.json
3. Verify GPU is being used (faster = GPU)
4. Check PaddleOCR model version

## Future Enhancement Areas

Ideas for improvement:
- Persistent job queue (SQLite/Redis)
- API authentication (API keys)
- Rate limiting
- Progress percentage in status
- Multi-worker support (currently limited to 1)
- Docker containerization
- Web UI for uploads
- Webhook notifications for job completion
- Batch result download (ZIP)
- Resume incomplete jobs after restart

## Related Documentation

- **README.md**: User-facing documentation
- **QUICK_START.md**: Fast setup guide
- **RUNPOD_DEPLOYMENT.md**: RunPod-specific deployment
- **server/DEPLOYMENT_INSTRUCTIONS.md**: Detailed deployment steps
- **server/CLIENT_TIMEOUT_CONFIG.md**: Timeout configuration details

## Contact & Support

For issues:
1. Check logs (server console output)
2. Verify configuration files
3. Test with `test_gpu.py` and health endpoint
4. Review this CLAUDE.md for common patterns
5. Check existing documentation in README.md

---

**Last Updated**: 2025-11-17
**Version**: 1.0
**Maintainer**: AI Assistant (Claude)
