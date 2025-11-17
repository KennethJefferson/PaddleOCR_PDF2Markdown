"""
Flask REST API server for PDF to Markdown conversion.

Provides endpoints for:
- PDF upload and job submission
- Job status checking
- Result retrieval
"""

import json
import logging
import os
import sys
from pathlib import Path

# CRITICAL: Set CUDNN library paths BEFORE importing PaddleOCR/PaddlePaddle
# This must be done before any paddle imports
nvidia_libs = [
    "/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib",
    "/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib",
    "/usr/local/lib/python3.10/dist-packages/nvidia/cufft/lib",
    "/usr/local/lib/python3.10/dist-packages/nvidia/curand/lib",
    "/usr/local/lib/python3.10/dist-packages/nvidia/cusolver/lib",
    "/usr/local/lib/python3.10/dist-packages/nvidia/cusparse/lib",
    "/usr/local/lib/python3.10/dist-packages/nvidia/nccl/lib"
]

# Add to LD_LIBRARY_PATH
current_ld = os.environ.get('LD_LIBRARY_PATH', '')
new_ld = ':'.join(nvidia_libs) + ':' + current_ld if current_ld else ':'.join(nvidia_libs)
os.environ['LD_LIBRARY_PATH'] = new_ld

# Set PaddlePaddle GPU flags
os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0.8'
os.environ['FLAGS_gpu_memory_growth'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from pdf_processor import PDFProcessor
from queue_manager import QueueManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Global variables
queue_manager = None
config = {}


def load_config(config_path: str = "config.json") -> dict:
    """Load server configuration from JSON file."""
    default_config = {
        "host": "0.0.0.0",
        "port": 5000,
        "num_workers": 1,
        "use_gpu": False,
        "lang": "en",
        "debug": False
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}, using defaults")

    return default_config


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "PDF to Markdown Converter",
        "version": "1.0.0"
    })


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get queue statistics."""
    stats = queue_manager.get_queue_stats()
    return jsonify(stats)


@app.route('/submit', methods=['POST'])
def submit_job():
    """
    Submit PDF file(s) for processing.

    Accepts:
    - Single file: multipart/form-data with 'file' field
    - Batch files: multipart/form-data with multiple 'files[]' fields

    Returns:
    - Single job: {"job_id": "...", "filename": "..."}
    - Batch jobs: {"jobs": [{"job_id": "...", "filename": "..."}, ...]}
    """
    # Check if files were uploaded
    if 'file' not in request.files and 'files[]' not in request.files:
        return jsonify({"error": "No file(s) provided"}), 400

    job_results = []

    # Handle single file upload
    if 'file' in request.files:
        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are accepted"}), 400

        # Read file data
        filename = secure_filename(file.filename)
        pdf_data = file.read()

        # Submit job
        job_id = queue_manager.submit_job(filename, pdf_data)

        return jsonify({
            "job_id": job_id,
            "filename": filename,
            "status": "queued"
        })

    # Handle batch file upload
    files = request.files.getlist('files[]')

    if not files:
        return jsonify({"error": "No files provided"}), 400

    for file in files:
        if file.filename == '':
            continue

        if not file.filename.lower().endswith('.pdf'):
            job_results.append({
                "filename": file.filename,
                "error": "Only PDF files are accepted",
                "status": "rejected"
            })
            continue

        # Read file data
        filename = secure_filename(file.filename)
        pdf_data = file.read()

        # Submit job
        try:
            job_id = queue_manager.submit_job(filename, pdf_data)
            job_results.append({
                "job_id": job_id,
                "filename": filename,
                "status": "queued"
            })
        except Exception as e:
            logger.error(f"Failed to submit job for {filename}: {e}")
            job_results.append({
                "filename": filename,
                "error": str(e),
                "status": "failed"
            })

    return jsonify({"jobs": job_results})


@app.route('/status/<job_id>', methods=['GET'])
def get_status(job_id: str):
    """
    Get status of a job.

    Returns:
    - Job status dict with state, timestamps, etc.
    - 404 if job not found
    """
    status = queue_manager.get_job_status(job_id)

    if not status:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(status)


@app.route('/result/<job_id>', methods=['GET'])
def get_result(job_id: str):
    """
    Get result of a completed job.

    Returns:
    - Markdown text and metadata if job is completed
    - Status info if job is still processing
    - Error message if job failed
    - 404 if job not found
    """
    result = queue_manager.get_job_result(job_id)

    if not result:
        # Check if job exists
        status = queue_manager.get_job_status(job_id)
        if not status:
            return jsonify({"error": "Job not found"}), 404

        # Job exists but not ready yet
        return jsonify({
            "job_id": job_id,
            "status": status["status"],
            "message": "Job not completed yet"
        }), 202  # Accepted but processing

    return jsonify(result)


@app.route('/batch/status', methods=['POST'])
def batch_status():
    """
    Get status of multiple jobs.

    Request body:
    {
        "job_ids": ["job1", "job2", ...]
    }

    Returns:
    {
        "results": [
            {"job_id": "job1", "status": "...", ...},
            {"job_id": "job2", "status": "...", ...}
        ]
    }
    """
    data = request.get_json()

    if not data or 'job_ids' not in data:
        return jsonify({"error": "Missing job_ids in request body"}), 400

    job_ids = data['job_ids']

    if not isinstance(job_ids, list):
        return jsonify({"error": "job_ids must be a list"}), 400

    results = []
    for job_id in job_ids:
        status = queue_manager.get_job_status(job_id)
        if status:
            results.append(status)
        else:
            results.append({
                "job_id": job_id,
                "error": "Job not found"
            })

    return jsonify({"results": results})


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({
        "error": "File too large",
        "max_size_mb": app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
    }), 413


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


def initialize_services(cfg: dict):
    """Initialize PDF processor and queue manager."""
    global queue_manager

    logger.info("Initializing PDF processor...")
    pdf_processor = PDFProcessor(cfg)

    logger.info("Initializing queue manager...")
    queue_manager = QueueManager(
        pdf_processor=pdf_processor,
        num_workers=cfg.get("num_workers", 1)
    )

    logger.info("Starting worker threads...")
    queue_manager.start()

    logger.info("Services initialized successfully")


def main():
    """Main entry point."""
    global config

    # Load configuration
    config = load_config()

    logger.info("=" * 60)
    logger.info("PDF to Markdown Conversion Server")
    logger.info("=" * 60)
    logger.info(f"Configuration: {json.dumps(config, indent=2)}")

    # Initialize services
    try:
        initialize_services(config)
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    # Start Flask server
    host = config.get("host", "0.0.0.0")
    port = config.get("port", 5000)
    debug = config.get("debug", False)

    logger.info(f"Starting Flask server on {host}:{port}")
    logger.info("=" * 60)

    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        queue_manager.stop()
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
