# RunPod Deployment Guide

This guide provides step-by-step instructions for deploying the PDF to Markdown conversion server on your RunPod instance.

## Your RunPod Instance Details

**Pod Name**: `subjective_blush_tiglon`

**Network Configuration**:
- HTTP Service Port: **7777** (Ready)
- SSH Access: `ssh 8gnd6ikrks6zxz-64411645@ssh.runpod.io -i ~/.ssh/id_ed25519`
- Direct TCP SSH: `ssh root@213.173.110.214 -p 19492 -i ~/.ssh/id_ed25519`
- Public IP: `213.173.110.214`

**HTTP Service URL**: Your server will be accessible at the HTTP proxy URL provided by RunPod for port 7777.

## Deployment Steps

### Step 1: Connect to RunPod

Using SSH:
```bash
ssh 8gnd6ikrks6zxz-64411645@ssh.runpod.io -i ~/.ssh/id_ed25519
```

Or use the Web Terminal in RunPod dashboard.

### Step 2: Upload Server Files

From your local machine, copy the server directory to RunPod:

```bash
# Using rsync (recommended)
rsync -avz -e "ssh -i ~/.ssh/id_ed25519 -p 19492" \
  ./server/ \
  root@213.173.110.214:/workspace/pdf2markdown/

# Or using SCP
scp -i ~/.ssh/id_ed25519 -P 19492 -r \
  ./server/ \
  root@213.173.110.214:/workspace/pdf2markdown/
```

### Step 3: Install Dependencies on RunPod

Once connected to RunPod:

```bash
cd /workspace/pdf2markdown
pip install -r requirements.txt
```

**For GPU Support** (recommended on RunPod):
```bash
# Check CUDA version
nvidia-smi

# Install PaddlePaddle GPU version (CUDA 11.8+)
pip install paddlepaddle-gpu

# Verify GPU is detected
python -c "import paddle; print('GPU Available:', paddle.is_compiled_with_cuda())"
```

### Step 4: Verify Configuration

Check that `config.json` is configured for port 7777:

```bash
cat config.json
```

Should show:
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

### Step 5: Start the Server

**Option A: Foreground (for testing)**:
```bash
python server.py
```

**Option B: Background (persistent)**:
```bash
# Using nohup
nohup python server.py > server.log 2>&1 &

# Or using screen (recommended)
screen -S pdf_server
python server.py
# Press Ctrl+A, then D to detach
```

**Option C: Using systemd (most robust)**:

Create service file:
```bash
cat > /etc/systemd/system/pdf2markdown.service << 'EOF'
[Unit]
Description=PDF to Markdown Conversion Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/pdf2markdown
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable pdf2markdown
systemctl start pdf2markdown

# Check status
systemctl status pdf2markdown

# View logs
journalctl -u pdf2markdown -f
```

### Step 6: Get Your HTTP Service URL

1. Go to RunPod dashboard
2. Click on your pod: `subjective_blush_tiglon`
3. Under "HTTP Services", find **Port 7777**
4. Copy the proxied domain URL (e.g., `https://8gnd6ikrks6zxz-7777.proxy.runpod.net`)

### Step 7: Test the Server

From within RunPod:
```bash
curl http://localhost:7777/health
```

From your local machine (use the HTTP Service URL from Step 6):
```bash
curl https://8gnd6ikrks6zxz-7777.proxy.runpod.net/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "PDF to Markdown Converter",
  "version": "1.0.0"
}
```

### Step 8: Update Client Configuration

On your **local machine**, edit `client/config.json`:

```json
{
  "server_url": "https://8gnd6ikrks6zxz-7777.proxy.runpod.net",
  "poll_interval": 3.0,
  "timeout": 600
}
```

**Note**: Replace the URL with your actual HTTP Service URL from Step 6.

### Step 9: Test End-to-End

From your local machine:

```bash
cd client
python client.py test.pdf
```

## Monitoring

### View Server Logs

**If using screen**:
```bash
screen -r pdf_server
```

**If using systemd**:
```bash
journalctl -u pdf2markdown -f
```

**If using nohup**:
```bash
tail -f server.log
```

### Check Queue Statistics

```bash
curl https://your-pod-url-7777.proxy.runpod.net/stats
```

### Monitor GPU Usage

```bash
watch -n 1 nvidia-smi
```

## Troubleshooting

### Server Won't Start

**Check if port 7777 is in use**:
```bash
netstat -tulpn | grep 7777
```

**Check Python path**:
```bash
which python
python --version  # Should be 3.10 or 3.11
```

**Check dependencies**:
```bash
pip list | grep -E "(flask|paddleocr|paddlepaddle)"
```

### GPU Not Detected

```bash
# Check CUDA
nvcc --version

# Check PaddlePaddle GPU support
python -c "import paddle; print(paddle.is_compiled_with_cuda())"

# Reinstall GPU version
pip uninstall paddlepaddle paddlepaddle-gpu
pip install paddlepaddle-gpu
```

### Client Can't Connect

1. **Verify server is running**:
   ```bash
   ps aux | grep server.py
   ```

2. **Test from RunPod itself**:
   ```bash
   curl http://localhost:7777/health
   ```

3. **Check HTTP Service URL**: Ensure you're using the correct proxied domain from RunPod dashboard

4. **Check firewall**: RunPod HTTP services should work automatically, but verify port 7777 is listed

### Models Not Downloading

PaddleOCR downloads models on first use. Ensure internet access:

```bash
# Test internet
ping -c 3 google.com

# Check model download location
ls -lh ~/.paddleocr/
```

## Performance Optimization

### GPU Memory

If you get out-of-memory errors:

Edit `server.py` and add GPU memory limit:
```python
import paddle
paddle.set_device('gpu:0')
paddle.device.cuda.set_device(0)
# Limit to 2GB
paddle.device.set_device('gpu:0')
```

Or set environment variable:
```bash
export FLAGS_fraction_of_gpu_memory_to_use=0.5  # Use 50% of GPU
python server.py
```

### Increase Workers

For powerful RunPod instances, increase workers in `config.json`:
```json
{
  "num_workers": 2
}
```

**Warning**: More workers = more GPU memory usage.

## Persistence

RunPod pods can be ephemeral. To persist your setup:

1. **Use Network Volumes**: Store the server code on a RunPod network volume
2. **Create Startup Script**: Add server startup to RunPod pod initialization
3. **Docker Image**: Create a custom Docker image with pre-installed dependencies

### Startup Script Example

Create `/workspace/startup.sh`:
```bash
#!/bin/bash
cd /workspace/pdf2markdown
pip install -r requirements.txt --quiet
screen -dmS pdf_server python server.py
echo "PDF server started"
```

Make it executable:
```bash
chmod +x /workspace/startup.sh
```

Add to RunPod pod startup commands in template.

## Security Considerations

Your current setup has **no authentication**. For production:

1. **Add API Key Authentication**: Modify `server.py` to require API keys
2. **Use HTTPS**: RunPod HTTP services are already HTTPS proxied
3. **Rate Limiting**: Add Flask-Limiter to prevent abuse
4. **File Size Limits**: Already configured (100MB max)

## Stopping the Server

**If using screen**:
```bash
screen -r pdf_server
# Press Ctrl+C to stop
```

**If using systemd**:
```bash
systemctl stop pdf2markdown
```

**If using nohup**:
```bash
pkill -f server.py
```

## Getting Help

1. Check server logs for errors
2. Test health endpoint: `/health`
3. Verify GPU availability: `nvidia-smi`
4. Check PaddleOCR installation: `pip show paddleocr`

## Summary

Your deployment checklist:

- [ ] Connect to RunPod via SSH
- [ ] Upload server files to `/workspace/pdf2markdown`
- [ ] Install dependencies with pip
- [ ] Verify config.json (port 7777, GPU enabled)
- [ ] Start server (screen/systemd/nohup)
- [ ] Get HTTP Service URL from RunPod dashboard
- [ ] Update client config.json with URL
- [ ] Test with client: `python client.py test.pdf`
- [ ] Monitor with `nvidia-smi` and logs

Your server URL will be: `https://8gnd6ikrks6zxz-7777.proxy.runpod.net` (or similar)
