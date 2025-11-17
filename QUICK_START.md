# Quick Start Guide

## TL;DR - Get Running in 5 Minutes

### 1. Deploy to RunPod (Windows)

```bash
# Run the deployment script
deploy_to_runpod.bat
```

Or manually:
```bash
scp -i %USERPROFILE%\.ssh\id_ed25519 -P 19492 -r server\* root@213.173.110.214:/workspace/pdf2markdown/
```

### 2. Start Server on RunPod

```bash
# SSH into RunPod
ssh root@213.173.110.214 -p 19492 -i ~/.ssh/id_ed25519

# Navigate to directory
cd /workspace/pdf2markdown

# Start server (quick test)
python server.py

# OR start in background (persistent)
screen -S pdf_server
python server.py
# Press Ctrl+A, then D to detach
```

### 3. Get Your Server URL

1. Go to RunPod dashboard
2. Click on pod: `subjective_blush_tiglon`
3. Find **Port 7777** under "HTTP Services"
4. Copy the URL (e.g., `https://8gnd6ikrks6zxz-7777.proxy.runpod.net`)

### 4. Update Client Config

Edit `client\config.json`:
```json
{
  "server_url": "https://YOUR-POD-ID-7777.proxy.runpod.net",
  "poll_interval": 3.0,
  "timeout": 600,
  "workers": 2
}
```

### 5. Install Client Dependencies

```bash
cd client
pip install -r requirements.txt
```

### 6. Convert PDFs

**Scan entire directory**:
```bash
# Non-recursive (only root folder)
python client.py -scan "C:\path\to\pdfs"

# Recursive (includes subfolders)
python client.py -scan "C:\path\to\pdfs" -recursive

# With parallel uploads and verbose output
python client.py -scan "C:\path\to\pdfs" -workers 2 -recursive -verbose
```

**Single file**:
```bash
python client.py C:\path\to\document.pdf
```

**Multiple files**:
```bash
python client.py file1.pdf file2.pdf file3.pdf
```

**Mixed mode** (directory + files):
```bash
python client.py -scan "C:\Books" "D:\report.pdf" -recursive
```

**Output Examples**:

Quiet mode (default):
```
✓ Completed: 45/50 files in 3m 45s
```

Verbose mode (`-verbose`):
```
Scanning: C:\PDFs (recursive)
Found 50 PDF files
Skipping 5 file(s) (already converted)
Converting 45 file(s) with 2 worker(s)...

[Worker 1] book1.pdf
  Uploading: book1.pdf (1.2 MB)
  Job ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Processing: book1.pdf
  ✓ Completed: book1.pdf → book1.md

============================================================
=== Conversion Summary ===
============================================================
Total PDFs found: 50
Already converted (skipped): 5
Submitted for conversion: 45
Successfully converted: 43
Failed: 2
Success rate: 95.6%
Total time: 3m 45s
Average: 5.2s per file
============================================================
```

## Key URLs

| Endpoint | URL | Description |
|----------|-----|-------------|
| Health Check | `/health` | Test server connectivity |
| Submit Job | `/submit` | Upload PDF (POST) |
| Check Status | `/status/{job_id}` | Get job status |
| Get Result | `/result/{job_id}` | Download markdown |
| Statistics | `/stats` | View queue stats |

## Testing

**Test server health**:
```bash
curl https://YOUR-POD-ID-7777.proxy.runpod.net/health
```

Expected response:
```json
{"status": "healthy", "service": "PDF to Markdown Converter", "version": "1.0.0"}
```

**Test with client**:
```bash
cd client
python client.py test.pdf
```

## Common Issues

### Server won't start
```bash
# Check if already running
ps aux | grep server.py

# Check port 7777
netstat -tulpn | grep 7777
```

### Client can't connect
1. Verify server is running: `ps aux | grep server.py`
2. Test health endpoint: `curl http://localhost:7777/health` (from RunPod)
3. Check URL in `client/config.json` is correct
4. Ensure you copied the full HTTPS URL from RunPod dashboard

### GPU not working
```bash
# Check GPU
nvidia-smi

# Install GPU version
pip install paddlepaddle-gpu
```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Server code | `/workspace/pdf2markdown/` (RunPod) | Server files |
| Client code | `client/` (local) | Upload tool |
| Input PDFs | Anywhere on local machine | Source files |
| Output markdown | Same directory as input PDFs | Converted files |

## Monitoring

**View server logs** (if using screen):
```bash
screen -r pdf_server
```

**Check GPU usage**:
```bash
watch -n 1 nvidia-smi
```

**Queue statistics**:
```bash
curl https://YOUR-POD-ID-7777.proxy.runpod.net/stats
```

## Performance

| Hardware | Speed | 100-Page PDF |
|----------|-------|--------------|
| CPU | ~3-4 sec/page | ~5-7 minutes |
| GPU (RunPod) | ~100ms/page | ~10 seconds |

## Next Steps

- Read full documentation: [README.md](README.md)
- RunPod deployment guide: [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md)
- Configure advanced settings in `server/config.json`

## Support Checklist

Before asking for help:

- [ ] Server is running: `ps aux | grep server.py`
- [ ] Health endpoint works: `curl http://localhost:7777/health`
- [ ] Client config has correct URL
- [ ] Dependencies installed: `pip list | grep paddleocr`
- [ ] GPU detected: `nvidia-smi` (on RunPod)
- [ ] Checked server logs for errors
