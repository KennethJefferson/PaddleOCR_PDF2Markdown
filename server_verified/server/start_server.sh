#!/bin/bash

# PDF to Markdown Server Startup Script
# This script properly configures the environment for GPU acceleration

echo "Starting PDF to Markdown Server with GPU Support..."

# Run GPU setup first (creates necessary symlinks)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -f "$DIR/setup_gpu.sh" ]; then
    bash "$DIR/setup_gpu.sh"
fi

# Set CUDA and CUDNN paths - CRITICAL for GPU processing
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cufft/lib:/usr/local/lib/python3.10/dist-packages/nvidia/curand/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cusolver/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cusparse/lib:/usr/local/lib/python3.10/dist-packages/nvidia/nccl/lib:$LD_LIBRARY_PATH"

# Set CUDA device (use 0 for first GPU)
export CUDA_VISIBLE_DEVICES=0

# PaddlePaddle GPU flags
export FLAGS_fraction_of_gpu_memory_to_use=0.8  # Use 80% of GPU memory
export FLAGS_gpu_memory_growth=1  # Enable dynamic GPU memory allocation

# Print environment info
echo "==========================================="
echo "GPU Information:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
echo "==========================================="
echo "CUDNN Library Path:"
echo $LD_LIBRARY_PATH | tr ':' '\n' | grep nvidia
echo "==========================================="

# Change to server directory
cd /workspace/server

# Start the server
echo "Starting server with GPU acceleration enabled..."
python server.py