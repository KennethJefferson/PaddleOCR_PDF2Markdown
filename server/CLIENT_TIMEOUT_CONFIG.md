# Client Timeout Configuration Guide

## Problem
Large PDF files (>10MB) may timeout during upload with the error:
```
HTTPSConnectionPool(host='...', port=443): Read timed out. (read timeout=30.0)
```

## Solution: Increase Client Timeout Settings

### Option 1: Modify Your Client Script

If you're using Python `requests` library, increase the timeout:

```python
import requests

# For single file upload - increase timeout to 300 seconds (5 minutes)
response = requests.post(
    f"{server_url}/submit",
    files={'file': pdf_data},
    timeout=(30, 300)  # (connection timeout, read timeout)
)

# Or for very large files - 10 minutes
response = requests.post(
    f"{server_url}/submit",
    files={'file': pdf_data},
    timeout=(30, 600)  # 10 minute read timeout
)
```

### Option 2: Dynamic Timeout Based on File Size

```python
def calculate_timeout(file_size_mb):
    """
    Calculate timeout based on file size
    Assumes ~1MB/s upload speed + processing time
    """
    base_timeout = 60  # Base 60 seconds
    per_mb_timeout = 15  # 15 seconds per MB
    return base_timeout + (file_size_mb * per_mb_timeout)

# Example usage
file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
timeout_seconds = calculate_timeout(file_size_mb)

response = requests.post(
    f"{server_url}/submit",
    files={'file': pdf_data},
    timeout=(30, timeout_seconds)
)
```

### Option 3: Command Line Client Update

If using the provided client.py script, you can add a timeout parameter:

```bash
# Add this to your client command
python client.py -scan "folder" -workers 2 -timeout 300
```

Or modify the client.py directly to use a higher default timeout:

```python
# In client.py, look for requests.post calls and update:
DEFAULT_TIMEOUT = (30, 300)  # 5 minute read timeout

# Then use it in all requests
response = self.session.post(url, timeout=DEFAULT_TIMEOUT, ...)
```

## Recommended Timeout Values

| File Size | Recommended Timeout |
|-----------|-------------------|
| < 5 MB    | 60 seconds        |
| 5-10 MB   | 120 seconds       |
| 10-20 MB  | 300 seconds (5 min) |
| 20-50 MB  | 600 seconds (10 min) |
| 50-100 MB | 900 seconds (15 min) |
| > 100 MB  | 1200 seconds (20 min) |

## Server-Side Considerations

The server has been configured to handle large files:
- Max file size: 500MB
- GPU processing: Enabled for faster OCR
- Progress tracking: Shows processing progress in logs

## Network Considerations

For RunPod proxy connections:
- The RunPod proxy may have its own timeout (usually 300s)
- Consider using direct connection if available
- For very large files, consider batch processing or file splitting

## Testing Your Configuration

Test with a large file to verify the timeout works:

```python
import time
import requests

def test_large_file_upload(server_url, pdf_path, timeout_seconds):
    start_time = time.time()

    try:
        with open(pdf_path, 'rb') as f:
            response = requests.post(
                f"{server_url}/submit",
                files={'file': ('test.pdf', f, 'application/pdf')},
                timeout=(30, timeout_seconds)
            )

        elapsed = time.time() - start_time
        print(f"✓ Upload successful in {elapsed:.1f} seconds")
        return response.json()

    except requests.Timeout:
        elapsed = time.time() - start_time
        print(f"✗ Timeout after {elapsed:.1f} seconds - increase timeout")
        return None
```

## Monitoring Progress

While processing, you can check the job status:

```python
def monitor_job(server_url, job_id, check_interval=5):
    while True:
        response = requests.get(f"{server_url}/status/{job_id}")
        status = response.json()

        print(f"Status: {status.get('status')} - {status.get('message', '')}")

        if status.get('status') in ['completed', 'failed']:
            break

        time.sleep(check_interval)

    return status
```