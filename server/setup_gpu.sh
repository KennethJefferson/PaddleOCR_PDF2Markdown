#!/bin/bash

# Setup GPU libraries for PaddlePaddle
echo "Setting up GPU libraries for PaddlePaddle..."

# Create CUDA directory if it doesn't exist
mkdir -p /usr/local/cuda/lib64

# Link all CUDNN libraries
echo "Linking CUDNN libraries..."
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn.so.9 /usr/local/cuda/lib64/libcudnn.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn.so.9 /usr/local/cuda/lib64/libcudnn.so.8
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_adv.so.9 /usr/local/cuda/lib64/libcudnn_adv.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_cnn.so.9 /usr/local/cuda/lib64/libcudnn_cnn.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_graph.so.9 /usr/local/cuda/lib64/libcudnn_graph.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_ops.so.9 /usr/local/cuda/lib64/libcudnn_ops.so

# Link CUBLAS libraries
echo "Linking CUBLAS libraries..."
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublas.so.12 /usr/local/cuda/lib64/libcublas.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublas.so.12 /usr/local/cuda/lib64/libcublas.so.11
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublasLt.so.12 /usr/local/cuda/lib64/libcublasLt.so

# Set environment variables
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH"

echo "GPU setup complete!"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"