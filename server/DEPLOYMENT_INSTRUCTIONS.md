# PDF to Markdown Server - RunPod Deployment Instructions

## Overview
This is a Flask-based REST API server that converts PDF files to Markdown using PaddleOCR with GPU acceleration.

## RunPod Configuration Requirements

### 1. GPU Template Selection
- **Minimum GPU**: NVIDIA RTX 3090 or better
- **VRAM**: At least 16GB
- **CUDA**: 11.x or 12.x compatible
- **Template**: Use Ubuntu 22.04 with PyTorch or CUDA base image

### 2. Network Configuration
- **HTTP Service Port**: 7777 (MUST be exposed)
- **Expose HTTP Ports**: Enable and set to 7777
- **Use the following network config in RunPod**:
  ```
  HTTP Service: Enabled
  Port: 7777
  ```

## Deployment Steps

### Step 1: Upload and Extract Files
```bash
# Upload the pdf_server_runpod.zip to your RunPod instance
# Extract the files
cd /workspace
unzip pdf_server_runpod.zip
cd server
```

### Step 2: Install Dependencies
```bash
# Install system dependencies
apt-get update
apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# Install Python packages (use exact versions for compatibility)
pip install --ignore-installed blinker flask
pip install -r requirements.txt
```

### Step 3: Verify GPU Setup
```bash
# Test GPU detection
python test_gpu.py

# If you see CUDNN errors, run the GPU setup:
bash setup_gpu.sh
```

### Step 4: Start the Server
```bash
# Option 1: Use the startup script (RECOMMENDED)
bash start_server.sh

# Option 2: Manual start with environment setup
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH"
export CUDA_VISIBLE_DEVICES=0
export FLAGS_fraction_of_gpu_memory_to_use=0.8
python server.py
```

### Step 5: Verify Server is Running
```bash
# Check health endpoint (from another terminal or using curl)
curl http://localhost:7777/health

# Should return:
# {
#   "status": "healthy",
#   "service": "PDF to Markdown Converter",
#   "version": "1.0.0"
# }
```

## API Endpoints

### 1. Health Check
```
GET /health
```

### 2. Submit PDF for Processing
```
POST /submit
Content-Type: multipart/form-data
Field: file (PDF file)

Returns: {"job_id": "...", "filename": "...", "status": "queued"}
```

### 3. Check Job Status
```
GET /status/<job_id>

Returns: Job status information
```

### 4. Get Results
```
GET /result/<job_id>

Returns: Markdown text when job is complete
```

### 5. Queue Statistics
```
GET /stats

Returns: Queue statistics including pending, processing, completed jobs
```

## Important Files

- **server.py**: Main Flask application
- **pdf_processor.py**: PDF to Markdown conversion logic using PaddleOCR
- **queue_manager.py**: Job queue management
- **config.json**: Server configuration (port, GPU settings)
- **setup_gpu.sh**: Creates necessary CUDNN library symlinks
- **start_server.sh**: Startup script with full environment setup
- **test_gpu.py**: GPU verification script
- **requirements.txt**: Python package dependencies

## Troubleshooting

### 1. CUDNN Library Errors
If you see errors about missing CUDNN libraries:
```bash
bash setup_gpu.sh
# Then restart the server
```

### 2. Port Already in Use
If port 7777 is already in use:
```bash
# Find and kill the process using port 7777
lsof -i :7777
kill -9 <PID>
```

### 3. GPU Not Detected
```bash
# Check NVIDIA drivers
nvidia-smi

# Verify CUDA is available
python -c "import paddle; print(paddle.is_compiled_with_cuda())"
```

### 4. Memory Issues
If you encounter GPU memory errors, adjust the memory fraction in server.py:
```python
os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0.6'  # Reduce from 0.8
```

## Package Versions (Critical for Compatibility)
- **PaddleOCR**: 2.8.1 (Uses PPStructure, not PPStructureV3)
- **PaddlePaddle-GPU**: 2.5.2
- **NumPy**: <2.0 (Required for compatibility)
- **Flask**: 3.0.3
- **Python**: 3.10

## Notes
- The server MUST run on port 7777 as configured
- GPU processing is essential for performance
- The server uses PaddleOCR 2.8.1 with PPStructure (older version for compatibility)
- All CUDNN library paths are automatically configured in server.py
- The server processes PDFs in a queue with configurable workers

## Support
For issues, check the logs and ensure all dependencies are correctly installed with the exact versions specified in requirements.txt.