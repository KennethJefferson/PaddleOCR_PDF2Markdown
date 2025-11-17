# PDF to Markdown Conversion Server

A Flask-based REST API server for converting PDF files to Markdown format using PaddleOCR.

## Features
- PDF to Markdown conversion using PaddleOCR
- GPU acceleration support
- Queue-based processing for handling multiple requests
- RESTful API endpoints
- Table and layout recognition

## Requirements
- Python 3.10+
- CUDA-compatible GPU (for GPU acceleration)
- RunPod or similar GPU environment

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: For GPU support, ensure CUDA is properly installed on your system.

2. Configure the server:
Edit `config.json` to set your desired configuration:
```json
{
  "host": "0.0.0.0",
  "port": 7777,
  "num_workers": 1,
  "use_gpu": true,
  "lang": "en",
  "debug": false
}
```

## Running the Server

```bash
cd /workspace/server
python server.py
```

The server will start on port 7777 (or as configured in config.json).

## API Endpoints

- `GET /health` - Health check
- `GET /stats` - Queue statistics
- `POST /submit` - Submit PDF for conversion
- `GET /status/<job_id>` - Check job status
- `GET /result/<job_id>` - Get conversion results
- `POST /batch/status` - Check multiple job statuses

## Usage Example

1. Submit a PDF:
```bash
curl -X POST -F "file=@document.pdf" http://localhost:7777/submit
```

2. Check status:
```bash
curl http://localhost:7777/status/<job_id>
```

3. Get results:
```bash
curl http://localhost:7777/result/<job_id>
```

## Important Notes

- This implementation uses PaddleOCR 2.8.1 with PPStructure (not PPStructureV3)
- PaddlePaddle-GPU 2.5.2 is required for compatibility
- NumPy version must be <2.0 for compatibility
- The server automatically downloads OCR models on first run

## Files

- `server.py` - Main Flask application
- `pdf_processor.py` - PDF to Markdown conversion logic
- `queue_manager.py` - Job queue management
- `config.json` - Server configuration
- `requirements.txt` - Python dependencies

## Troubleshooting

If you encounter Flask installation issues due to blinker conflicts:
```bash
pip install --ignore-installed blinker flask
```

For GPU memory issues, adjust the GPU memory allocation in your environment variables.