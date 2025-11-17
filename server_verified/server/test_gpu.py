#!/usr/bin/env python3
"""
Test GPU and CUDNN setup for PaddleOCR
"""

import os
import sys

# Set CUDNN library paths BEFORE importing paddle
nvidia_libs = [
    "/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib",
    "/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib",
]

# Add to LD_LIBRARY_PATH
current_ld = os.environ.get('LD_LIBRARY_PATH', '')
new_ld = ':'.join(nvidia_libs) + ':' + current_ld if current_ld else ':'.join(nvidia_libs)
os.environ['LD_LIBRARY_PATH'] = new_ld

print("=" * 60)
print("Testing GPU Setup for PaddleOCR")
print("=" * 60)

# Check CUDA environment
print("\n1. CUDA Environment:")
print(f"   CUDA_VISIBLE_DEVICES: {os.environ.get('CUDA_VISIBLE_DEVICES', 'Not set')}")
print(f"   LD_LIBRARY_PATH includes nvidia: {'nvidia' in os.environ.get('LD_LIBRARY_PATH', '')}")

# Try importing paddle
try:
    import paddle
    print("\n2. PaddlePaddle Import: ✓ Success")
    print(f"   PaddlePaddle version: {paddle.__version__}")

    # Check GPU availability
    print("\n3. GPU Detection:")
    gpu_available = paddle.is_compiled_with_cuda()
    print(f"   Compiled with CUDA: {gpu_available}")

    if gpu_available:
        gpu_count = paddle.device.cuda.device_count()
        print(f"   GPU count: {gpu_count}")

        # Try to use GPU
        try:
            paddle.set_device('gpu:0')
            print("   Set device to GPU: ✓ Success")

            # Create a simple tensor on GPU
            x = paddle.rand([2, 2])
            print(f"   Created tensor on: {x.place}")
            print("   GPU is working!")
        except Exception as e:
            print(f"   Error setting GPU device: {e}")
    else:
        print("   WARNING: PaddlePaddle not compiled with CUDA support!")

except ImportError as e:
    print(f"\n2. PaddlePaddle Import: ✗ Failed")
    print(f"   Error: {e}")
    sys.exit(1)

# Try importing PaddleOCR
try:
    from paddleocr import PPStructure
    print("\n4. PaddleOCR Import: ✓ Success")

    # Try initializing PPStructure with GPU
    try:
        print("\n5. Initializing PPStructure with GPU...")
        structure = PPStructure(
            use_gpu=True,
            lang='en',
            show_log=False
        )
        print("   PPStructure initialization: ✓ Success")
        print("   GPU processing is ready!")
    except Exception as e:
        print(f"   PPStructure initialization: ✗ Failed")
        print(f"   Error: {e}")

except ImportError as e:
    print(f"\n4. PaddleOCR Import: ✗ Failed")
    print(f"   Error: {e}")

print("\n" + "=" * 60)