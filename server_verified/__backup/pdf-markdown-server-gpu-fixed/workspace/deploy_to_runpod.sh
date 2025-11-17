#!/bin/bash

# Deployment script for RunPod
# This script uploads the server directory to your RunPod instance

# RunPod connection details
RUNPOD_HOST="213.173.110.214"
RUNPOD_PORT="19492"
RUNPOD_USER="root"
SSH_KEY="$HOME/.ssh/id_ed25519"
REMOTE_DIR="/workspace/pdf2markdown"

echo "========================================="
echo "  PDF to Markdown - RunPod Deployment"
echo "========================================="
echo ""

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at $SSH_KEY"
    echo "Please update the SSH_KEY variable in this script"
    exit 1
fi

# Create remote directory
echo "Step 1: Creating remote directory..."
ssh -i "$SSH_KEY" -p "$RUNPOD_PORT" "$RUNPOD_USER@$RUNPOD_HOST" \
    "mkdir -p $REMOTE_DIR"

# Upload server files
echo ""
echo "Step 2: Uploading server files..."
rsync -avz -e "ssh -i $SSH_KEY -p $RUNPOD_PORT" \
    --progress \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".git" \
    ./server/ \
    "$RUNPOD_USER@$RUNPOD_HOST:$REMOTE_DIR/"

if [ $? -ne 0 ]; then
    echo "Error: Failed to upload files"
    exit 1
fi

echo ""
echo "Step 3: Installing dependencies..."
ssh -i "$SSH_KEY" -p "$RUNPOD_PORT" "$RUNPOD_USER@$RUNPOD_HOST" << 'ENDSSH'
cd /workspace/pdf2markdown
echo "Installing requirements..."
pip install -r requirements.txt --quiet

echo ""
echo "Checking GPU availability..."
python -c "import paddle; print('GPU Available:', paddle.is_compiled_with_cuda())" 2>/dev/null || echo "PaddlePaddle not yet configured for GPU"

echo ""
echo "Server files:"
ls -lh
ENDSSH

echo ""
echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. SSH into RunPod:"
echo "   ssh -i $SSH_KEY -p $RUNPOD_PORT $RUNPOD_USER@$RUNPOD_HOST"
echo ""
echo "2. Start the server:"
echo "   cd $REMOTE_DIR"
echo "   screen -S pdf_server"
echo "   python server.py"
echo ""
echo "3. Get your HTTP Service URL from RunPod dashboard (Port 7777)"
echo ""
echo "4. Update client/config.json with the URL"
echo ""
echo "5. Test from local machine:"
echo "   cd client"
echo "   python client.py test.pdf"
echo ""
