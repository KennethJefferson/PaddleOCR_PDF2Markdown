# PDF to Markdown Converter

A client-server application for converting PDF files to Markdown format using PaddleOCR's PP-StructureV3 document parsing pipeline.

## Features

- **REST API Server**: Flask-based server with job queueing system
- **CLI Client**: Command-line tool for uploading PDFs and retrieving results
- **Batch Processing**: Submit multiple PDFs at once
- **Status Tracking**: Monitor job progress (queued → processing → completed)
- **Layout Preservation**: Maintains document structure, tables, formulas, and images
- **Multi-language Support**: 100+ languages supported by PaddleOCR
- **GPU Acceleration**: Optional GPU support for faster processing

## Architecture

```
Client                    Server
  |                         |
  | POST /submit (PDF)      |
  |------------------------>|
  |   job_id                | → Queue
  |<------------------------|
  |                         | → Worker processes PDF
  | GET /status/{job_id}    |
  |------------------------>|
  |   status: processing    |
  |<------------------------|
  |                         |
  | GET /result/{job_id}    |
  |------------------------>|
  |   markdown text         |
  |<------------------------|
  | Save .md file           |
```

## Installation

### Server Setup

1. **Requirements**:
   - Python 3.10 or 3.11 (recommended for best compatibility)
   - 2-4GB RAM minimum
   - GPU (optional, for faster processing)

2. **Install Dependencies**:
   ```bash
   cd server
   pip install -r requirements.txt
   ```

   For GPU support (NVIDIA CUDA 11.8+):
   ```bash
   pip uninstall paddlepaddle
   pip install paddlepaddle-gpu>=3.0.0
   ```

3. **Configure Server**:
   Edit `server/config.json`:
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

   Options:
   - `host`: Server bind address (`0.0.0.0` for all interfaces)
   - `port`: Server port (default: 5000)
   - `num_workers`: Number of processing workers (1 recommended)
   - `use_gpu`: Enable GPU acceleration (requires CUDA)
   - `lang`: Language code (`en`, `ch`, etc.)
   - `debug`: Enable Flask debug mode

4. **Start Server**:
   ```bash
   cd server
   python server.py
   ```

   Server will be available at `http://localhost:5000`

### Client Setup

1. **Install Dependencies**:
   ```bash
   cd client
   pip install -r requirements.txt
   ```

2. **Configure Client**:
   Edit `client/config.json`:
   ```json
   {
     "server_url": "http://localhost:5000",
     "poll_interval": 2.0,
     "timeout": 300,
     "workers": 2
   }
   ```

   Options:
   - `server_url`: Server endpoint (update for RunPod/remote servers)
   - `poll_interval`: Seconds between status checks (default: 2.0)
   - `timeout`: Max seconds to wait for completion (default: 300)
   - `workers`: Number of parallel upload workers (default: 2)

## Usage

### Server API Endpoints

**Health Check**:
```bash
GET /health
```

**Submit PDF** (single file):
```bash
POST /submit
Content-Type: multipart/form-data
file: <pdf_file>
```

**Submit Batch**:
```bash
POST /submit
Content-Type: multipart/form-data
files[]: <pdf_file_1>
files[]: <pdf_file_2>
...
```

**Check Status**:
```bash
GET /status/{job_id}
```

**Get Result**:
```bash
GET /result/{job_id}
```

**Queue Statistics**:
```bash
GET /stats
```

### Client CLI

**Directory Scanning**:
```bash
# Scan directory (non-recursive)
python client.py -scan "C:\PDFs"

# Scan directory recursively
python client.py -scan "C:\PDFs" -recursive

# Scan with parallel uploads
python client.py -scan "C:\PDFs" -workers 2 -recursive

# Verbose output with details
python client.py -scan "C:\PDFs" -workers 2 -recursive -verbose
```

**Single File**:
```bash
python client.py document.pdf
```

Output: `document.md` in same directory

**Multiple Files**:
```bash
python client.py file1.pdf file2.pdf file3.pdf
```

**Mixed Mode** (auto-detect):
```bash
# Process directory + specific files
python client.py -scan "C:\PDFs" "D:\report.pdf" -recursive
```

**Custom Server URL**:
```bash
python client.py --server https://your-server:7777 -scan "C:\PDFs" -recursive
```

**CLI Flags**:
- `-scan <dir>` - Scan directory for PDFs
- `-workers <N>` - Number of parallel upload workers (default: from config or 1)
- `-recursive` - Search subdirectories for PDFs
- `-verbose` - Show detailed output (default: quiet mode)
- `--server <url>` - Override server URL from config
- `--config <path>` - Config file path (default: config.json)

**Output Modes**:
- **Quiet (default)**: Only errors and final summary
  ```
  ✓ Completed: 45/50 files in 3m 45s
  ```
- **Verbose (`-verbose`)**: Detailed progress and statistics
  ```
  Scanning: C:\PDFs (recursive)
  Found 50 PDF files
  Converting 50 file(s) with 2 worker(s)...
  [Worker 1] book1.pdf
    Uploading: book1.pdf (1.2 MB)
    Job ID: a1b2c3d4...
    ✓ Completed: book1.pdf → book1.md

  === Conversion Summary ===
  Total PDFs found: 50
  Successfully converted: 45
  Failed: 5
  Success rate: 90.0%
  Total time: 3m 45s
  Average: 5.0s per file
  ```

### Example Workflow

1. **Start Server** (on RunPod or local machine):
   ```bash
   cd server
   python server.py
   ```

2. **Convert PDFs** (from client machine):
   ```bash
   cd client

   # Single file
   python client.py C:\path\to\report.pdf

   # Entire directory
   python client.py -scan C:\path\to\pdfs -recursive

   # With parallel uploads and verbose output
   python client.py -scan C:\path\to\pdfs -workers 2 -recursive -verbose
   ```

3. **Result**:
   - Input: `C:\path\to\pdfs\report.pdf`
   - Output: `C:\path\to\pdfs\report.md`
   - Images: `C:\path\to\pdfs\images\` (if any embedded images)

### Batch Examples

**Scan entire directory tree**:
```bash
python client.py -scan "C:\Documents\PDFs" -recursive -workers 2
```

**Scan multiple directories**:
```bash
python client.py -scan "C:\Books" -scan "D:\Reports" -recursive
```

**Mix directories and specific files**:
```bash
python client.py -scan "C:\Books" "D:\report.pdf" "D:\document.pdf" -recursive
```

**Process with wildcards** (Windows PowerShell):
```powershell
Get-ChildItem C:\PDFs -Filter *.pdf | ForEach-Object { python client.py $_.FullName }
```

**Verbose mode for debugging**:
```bash
python client.py -scan "C:\PDFs" -workers 2 -recursive -verbose
```

## Configuration for RunPod

### Server (RunPod Instance)

1. **Update config.json**:
   ```json
   {
     "host": "0.0.0.0",
     "port": 5000,
     "num_workers": 1,
     "use_gpu": true,
     "lang": "en"
   }
   ```

2. **Expose Port**: Configure RunPod to expose port 5000

3. **Get Public URL**: Note the RunPod public endpoint (e.g., `https://xyz.runpod.net`)

### Client (Local Machine)

Update `client/config.json`:
```json
{
  "server_url": "https://xyz.runpod.net",
  "poll_interval": 3.0,
  "timeout": 600,
  "workers": 2
}
```

Options:
- `server_url`: Server endpoint URL
- `poll_interval`: Seconds between status checks (default: 3.0)
- `timeout`: Max seconds to wait for completion (default: 600)
- `workers`: Number of parallel upload workers (default: 2)

## Output Format

### Markdown Structure

The converted markdown preserves:
- Document hierarchy (titles, headings, paragraphs)
- Tables (converted to markdown table format)
- Lists and bullet points
- Text formatting
- Formulas (as LaTeX)
- Images (extracted and referenced)

Example output:
```markdown
# Document Title

## Section 1

This is a paragraph with recognized text...

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

![image_1](./images/page_1_img_1.png)

### Subsection

More text content...
```

### Images

If the PDF contains images, they are extracted to an `images/` subdirectory alongside the markdown file:
```
/path/to/
  ├── document.pdf
  ├── document.md
  └── images/
      ├── page_1_img_1.png
      ├── page_2_img_1.png
      └── ...
```

## Performance

### CPU Performance
- **Speed**: ~3-4 seconds per page
- **RAM**: 2-4GB
- **Use Case**: Small batches, development

### GPU Performance
- **Speed**: ~100ms per page (30-40x faster)
- **VRAM**: 1-2GB minimum
- **Use Case**: Production, large batches

### Benchmarks

| Hardware | Pages/Second | 100-Page PDF |
|----------|--------------|--------------|
| CPU (8-core) | 0.25-0.33 | ~5-7 minutes |
| GPU (RTX 3090) | 10-15 | ~6-10 seconds |

## Troubleshooting

### PyMuPDF Compatibility Issues

If you encounter errors with PyMuPDF on Python 3.11+:
```bash
pip install PyMuPDF==1.20.0
```

### GPU Not Detected

Check CUDA installation:
```bash
python -c "import paddle; print(paddle.is_compiled_with_cuda())"
```

If False, reinstall with GPU support:
```bash
pip uninstall paddlepaddle paddlepaddle-gpu
pip install paddlepaddle-gpu
```

### Server Connection Refused

Check firewall rules and ensure server is running:
```bash
curl http://localhost:5000/health
```

### Memory Issues

For very large PDFs, the server processes them page-by-page, but you may need to:
1. Reduce batch size
2. Increase timeout in client config
3. Add more RAM/VRAM

## Development

### Project Structure

```
PaddleOCR_PDF2Markdown/
├── server/
│   ├── server.py           # Flask REST API
│   ├── queue_manager.py    # Job queue handler
│   ├── pdf_processor.py    # PaddleOCR integration
│   ├── config.json         # Server configuration
│   └── requirements.txt
├── client/
│   ├── client.py           # CLI client
│   ├── config.json         # Client configuration
│   └── requirements.txt
└── README.md
```

### Testing

**Test Server Locally**:
```bash
# Terminal 1: Start server
cd server
python server.py

# Terminal 2: Test with client
cd client
python client.py test.pdf
```

**Test PDF Processor Directly**:
```bash
cd server
python pdf_processor.py test.pdf
```

### API Testing with cURL

**Submit Job**:
```bash
curl -X POST http://localhost:5000/submit \
  -F "file=@document.pdf"
```

**Check Status**:
```bash
curl http://localhost:5000/status/JOB_ID
```

**Get Result**:
```bash
curl http://localhost:5000/result/JOB_ID
```

## Limitations

- Input: PDF files only
- Output: Markdown (`.md`) files
- Queue: In-memory (jobs lost on server restart)
- Authentication: None (suitable for private networks)
- OCR quality depends on PDF quality (scanned documents may need tuning)

## Future Enhancements

- [ ] Persistent queue (SQLite/Redis)
- [ ] API key authentication
- [ ] Rate limiting
- [ ] Progress percentage in status endpoint
- [ ] Multi-worker support
- [ ] Docker containerization
- [ ] Web UI for uploads

## License

This project uses PaddleOCR which is licensed under Apache License 2.0.

## Credits

- **PaddleOCR**: https://github.com/PaddlePaddle/PaddleOCR
- **PP-StructureV3**: Document parsing pipeline
- **Flask**: Web framework
- **PyMuPDF**: PDF processing library
