#!/bin/bash

# Setup GPU libraries for PaddlePaddle
echo "Setting up GPU libraries for PaddlePaddle..."

# Create CUDA directory if it doesn't exist
mkdir -p /usr/local/cuda/lib64

# Link all CUDNN libraries (comprehensive)
echo "Linking CUDNN libraries..."
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn.so.9 /usr/local/cuda/lib64/libcudnn.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn.so.9 /usr/local/cuda/lib64/libcudnn.so.8
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_adv.so.9 /usr/local/cuda/lib64/libcudnn_adv.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_cnn.so.9 /usr/local/cuda/lib64/libcudnn_cnn.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_graph.so.9 /usr/local/cuda/lib64/libcudnn_graph.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_ops.so.9 /usr/local/cuda/lib64/libcudnn_ops.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_engines_precompiled.so.9 /usr/local/cuda/lib64/libcudnn_engines_precompiled.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_engines_runtime_compiled.so.9 /usr/local/cuda/lib64/libcudnn_engines_runtime_compiled.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib/libcudnn_heuristic.so.9 /usr/local/cuda/lib64/libcudnn_heuristic.so

# Link CUBLAS libraries
echo "Linking CUBLAS libraries..."
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublas.so.12 /usr/local/cuda/lib64/libcublas.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublas.so.12 /usr/local/cuda/lib64/libcublas.so.11
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublas.so.12 /usr/local/cuda/lib64/libcublas.so.12
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublasLt.so.12 /usr/local/cuda/lib64/libcublasLt.so
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublasLt.so.12 /usr/local/cuda/lib64/libcublasLt.so.11
ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib/libcublasLt.so.12 /usr/local/cuda/lib64/libcublasLt.so.12

# Link CUFFT libraries (needed for some operations)
echo "Linking CUFFT libraries..."
if [ -d "/usr/local/lib/python3.10/dist-packages/nvidia/cufft/lib" ]; then
    ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/cufft/lib/libcufft.so.11 /usr/local/cuda/lib64/libcufft.so 2>/dev/null
fi

# Link CURAND libraries
echo "Linking CURAND libraries..."
if [ -d "/usr/local/lib/python3.10/dist-packages/nvidia/curand/lib" ]; then
    ln -sf /usr/local/lib/python3.10/dist-packages/nvidia/curand/lib/libcurand.so.10 /usr/local/cuda/lib64/libcurand.so 2>/dev/null
fi

# Set environment variables
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH"

echo "GPU setup complete!"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
echo ""
echo "IMPORTANT: You must restart the Python server after running this script!"