"""
CLI client for PDF to Markdown conversion service.

Scans directories for PDFs, uploads them to the server in parallel,
and saves markdown files to the same directory as input PDFs.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import requests


@dataclass
class ConversionStats:
    """Track conversion statistics."""
    total_found: int = 0
    already_converted: int = 0
    submitted: int = 0
    completed: int = 0
    failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (filename, error)

    def start(self):
        """Mark start time."""
        self.start_time = datetime.now()

    def finish(self):
        """Mark end time."""
        self.end_time = datetime.now()

    def duration(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.submitted == 0:
            return 0.0
        return (self.completed / self.submitted) * 100

    def print_summary(self, verbose: bool = False):
        """Print conversion summary."""
        if not verbose:
            # Quiet mode: one-line summary
            if self.failed > 0:
                status = "✗" if self.completed == 0 else "⚠"
            else:
                status = "✓"

            duration = self.duration()
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

            if self.failed > 0:
                print(f"{status} Completed: {self.completed}/{self.submitted} files ({self.failed} failed) in {time_str}")
            else:
                print(f"{status} Completed: {self.completed}/{self.submitted} files in {time_str}")
        else:
            # Verbose mode: detailed summary
            print("\n" + "=" * 60)
            print("=== Conversion Summary ===")
            print("=" * 60)
            print(f"Total PDFs found: {self.total_found}")
            if self.already_converted > 0:
                print(f"Already converted (skipped): {self.already_converted}")
            print(f"Submitted for conversion: {self.submitted}")
            print(f"Successfully converted: {self.completed}")
            if self.failed > 0:
                print(f"Failed: {self.failed}")
            print(f"Success rate: {self.success_rate():.1f}%")

            duration = self.duration()
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"Total time: {minutes}m {seconds}s" if minutes > 0 else f"Total time: {seconds}s")

            if self.submitted > 0:
                avg_time = duration / self.submitted
                print(f"Average: {avg_time:.1f}s per file")

            if self.errors and verbose:
                print("\n--- Errors ---")
                for filename, error in self.errors:
                    print(f"  ✗ {filename}: {error}")
            print("=" * 60)


class PDFConverterClient:
    """Client for PDF to Markdown conversion API."""

    def __init__(self, server_url: str, poll_interval: float = 2.0, timeout: int = 300, verbose: bool = False):
        """
        Initialize the client.

        Args:
            server_url: Base URL of the server
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait for job completion
            verbose: Enable verbose output
        """
        self.server_url = server_url.rstrip('/')
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.verbose = verbose

    def log(self, message: str):
        """Log message if verbose mode enabled."""
        if self.verbose:
            print(message)

    def health_check(self) -> bool:
        """Check if server is healthy."""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            print(f"✗ Error connecting to server: {e}")
            return False

    def submit_pdf(self, pdf_path: str) -> Optional[str]:
        """Submit a single PDF file and return job_id."""
        if not os.path.exists(pdf_path):
            return None

        try:
            # Calculate dynamic timeout based on file size
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            read_timeout = max(60, 60 + (file_size_mb * 15))  # Min 60s, +15s per MB

            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                response = requests.post(
                    f"{self.server_url}/submit",
                    files=files,
                    timeout=(30, read_timeout)  # (connect_timeout, read_timeout)
                )

            if response.status_code == 200:
                data = response.json()
                return data.get('job_id')
            else:
                self.log(f"  ✗ Error submitting {os.path.basename(pdf_path)}: {response.status_code}")
                return None

        except Exception as e:
            self.log(f"  ✗ Error submitting {os.path.basename(pdf_path)}: {e}")
            return None

    def get_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a job."""
        try:
            response = requests.get(f"{self.server_url}/status/{job_id}", timeout=5.0)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def get_result(self, job_id: str) -> Optional[Dict]:
        """Get result of a completed job."""
        try:
            response = requests.get(f"{self.server_url}/result/{job_id}", timeout=10.0)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def wait_for_completion(self, job_id: str, filename: str) -> Optional[Dict]:
        """Wait for a job to complete."""
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed > self.timeout:
                return None

            status = self.get_status(job_id)
            if not status:
                return None

            job_status = status.get('status')

            if job_status == 'completed':
                return self.get_result(job_id)
            elif job_status == 'failed':
                return None

            time.sleep(self.poll_interval)

    def process_pdf(self, pdf_path: str, stats: ConversionStats) -> bool:
        """
        Process a single PDF file.

        Args:
            pdf_path: Path to PDF file
            stats: Statistics tracker

        Returns:
            True if successful, False otherwise
        """
        filename = os.path.basename(pdf_path)

        # Submit job
        self.log(f"  Uploading: {filename} ({self._format_size(os.path.getsize(pdf_path))})")
        job_id = self.submit_pdf(pdf_path)

        if not job_id:
            stats.failed += 1
            stats.errors.append((filename, "Failed to submit"))
            return False

        self.log(f"  Job ID: {job_id}")
        stats.submitted += 1

        # Wait for completion
        self.log(f"  Processing: {filename}")
        result = self.wait_for_completion(job_id, filename)

        if not result or not result.get('markdown'):
            error = result.get('error', 'Unknown error') if result else 'Timeout'
            stats.failed += 1
            stats.errors.append((filename, error))
            if not self.verbose:
                print(f"✗ Error processing {filename}: {error}")
            else:
                self.log(f"  ✗ Failed: {filename} - {error}")
            return False

        # Save markdown
        output_path = Path(pdf_path).with_suffix('.md')
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result['markdown'])

            stats.completed += 1
            self.log(f"  ✓ Completed: {filename} → {output_path.name}")
            return True

        except Exception as e:
            stats.failed += 1
            stats.errors.append((filename, f"Save error: {e}"))
            if not self.verbose:
                print(f"✗ Error saving {filename}: {e}")
            else:
                self.log(f"  ✗ Save failed: {filename} - {e}")
            return False

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def scan_directory(directory: str, recursive: bool = False, verbose: bool = False) -> List[str]:
    """
    Scan directory for PDF files.

    Args:
        directory: Directory to scan
        recursive: Search subdirectories
        verbose: Show scanning progress

    Returns:
        List of PDF file paths
    """
    pdf_files = []
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"✗ Error: Directory not found: {directory}")
        return []

    if not dir_path.is_dir():
        print(f"✗ Error: Not a directory: {directory}")
        return []

    if verbose:
        print(f"Scanning: {directory} ({'recursive' if recursive else 'non-recursive'})")

    if recursive:
        for pdf_file in dir_path.rglob('*.pdf'):
            if pdf_file.is_file():
                pdf_files.append(str(pdf_file))
    else:
        for pdf_file in dir_path.glob('*.pdf'):
            if pdf_file.is_file():
                pdf_files.append(str(pdf_file))

    if verbose:
        print(f"Found {len(pdf_files)} PDF file(s)")

    return pdf_files


def filter_already_converted(pdf_files: List[str], verbose: bool = False) -> List[str]:
    """
    Filter out PDFs that already have .md files.

    Args:
        pdf_files: List of PDF file paths
        verbose: Show skip messages

    Returns:
        List of PDFs that need conversion
    """
    to_convert = []
    skipped = 0

    for pdf_file in pdf_files:
        md_file = Path(pdf_file).with_suffix('.md')
        if md_file.exists():
            skipped += 1
        else:
            to_convert.append(pdf_file)

    if skipped > 0 and verbose:
        print(f"Skipping {skipped} file(s) (already converted)")

    return to_convert, skipped


def worker_process_pdf(client: PDFConverterClient, pdf_path: str, stats: ConversionStats, worker_id: int) -> bool:
    """Worker function to process a PDF."""
    if client.verbose:
        print(f"[Worker {worker_id}] {os.path.basename(pdf_path)}")
    return client.process_pdf(pdf_path, stats)


def parse_arguments(args: List[str]) -> Dict:
    """
    Parse command-line arguments.

    Returns:
        Dict with parsed arguments
    """
    config = {
        'scan_dirs': [],
        'files': [],
        'workers': 1,
        'recursive': False,
        'verbose': False,
        'server': None,
        'config_file': 'config.json'
    }

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '-scan' and i + 1 < len(args):
            config['scan_dirs'].append(args[i + 1])
            i += 2
        elif arg == '-workers' and i + 1 < len(args):
            try:
                config['workers'] = int(args[i + 1])
            except ValueError:
                print(f"✗ Error: Invalid workers value: {args[i + 1]}")
                sys.exit(1)
            i += 2
        elif arg == '-recursive':
            config['recursive'] = True
            i += 1
        elif arg == '-verbose':
            config['verbose'] = True
            i += 1
        elif arg == '--server' and i + 1 < len(args):
            config['server'] = args[i + 1]
            i += 2
        elif arg == '--config' and i + 1 < len(args):
            config['config_file'] = args[i + 1]
            i += 2
        elif not arg.startswith('-'):
            # Auto-detect: file or directory
            if os.path.isdir(arg):
                config['scan_dirs'].append(arg)
            elif os.path.isfile(arg) and arg.lower().endswith('.pdf'):
                config['files'].append(arg)
            else:
                print(f"✗ Error: Not a valid PDF file or directory: {arg}")
                sys.exit(1)
            i += 1
        else:
            print(f"✗ Error: Unknown argument: {arg}")
            sys.exit(1)

    return config


def load_config(config_path: str) -> dict:
    """Load client configuration."""
    default_config = {
        "server_url": "http://localhost:5000",
        "poll_interval": 2.0,
        "timeout": 300,
        "workers": 1
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                # Filter out comments
                loaded_config = {k: v for k, v in loaded_config.items() if not k.startswith('_')}
                default_config.update(loaded_config)
        except Exception as e:
            print(f"⚠ Warning: Failed to load config: {e}")

    return default_config


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments(sys.argv[1:])

    # Show usage if no inputs
    if not args['scan_dirs'] and not args['files']:
        print("PDF to Markdown Converter Client")
        print("\nUsage:")
        print("  python client.py -scan <directory> [-workers N] [-recursive] [-verbose]")
        print("  python client.py <file1.pdf> <file2.pdf> ... [-workers N] [-verbose]")
        print("  python client.py <directory> <file.pdf> [-recursive] [-verbose]")
        print("\nFlags:")
        print("  -scan <dir>      Scan directory for PDFs")
        print("  -workers <N>     Number of parallel upload workers (default: 1)")
        print("  -recursive       Search subdirectories for PDFs")
        print("  -verbose         Show detailed output")
        print("  --server <url>   Override server URL from config")
        print("  --config <path>  Config file path (default: config.json)")
        print("\nExamples:")
        print('  python client.py -scan "C:\\PDFs" -workers 2 -recursive -verbose')
        print('  python client.py document.pdf report.pdf -verbose')
        print('  python client.py "C:\\PDFs" document.pdf -recursive')
        sys.exit(0)

    # Load configuration
    config = load_config(args['config_file'])

    # Override server URL if provided
    if args['server']:
        config['server_url'] = args['server']

    # Override workers if provided
    if args['workers'] > 1:
        config['workers'] = args['workers']

    verbose = args['verbose']

    # Initialize client
    client = PDFConverterClient(
        server_url=config['server_url'],
        poll_interval=config.get('poll_interval', 2.0),
        timeout=config.get('timeout', 300),
        verbose=verbose
    )

    # Check server health
    if verbose:
        print(f"Connecting to server: {config['server_url']}")

    if not client.health_check():
        print(f"✗ Error: Server is not responding at {config['server_url']}")
        sys.exit(1)

    if verbose:
        print("✓ Server is healthy\n")

    # Collect all PDF files
    all_pdfs = []
    stats = ConversionStats()

    # Scan directories
    for scan_dir in args['scan_dirs']:
        pdfs = scan_directory(scan_dir, args['recursive'], verbose)
        all_pdfs.extend(pdfs)

    # Add direct files
    all_pdfs.extend(args['files'])

    if not all_pdfs:
        print("✗ No PDF files found")
        sys.exit(1)

    stats.total_found = len(all_pdfs)

    # Filter already converted
    to_convert, skipped = filter_already_converted(all_pdfs, verbose)
    stats.already_converted = skipped

    if not to_convert:
        print("✓ All PDFs already converted")
        sys.exit(0)

    # Start processing
    stats.start()

    if verbose:
        print(f"Converting {len(to_convert)} file(s) with {args['workers']} worker(s)...\n")

    # Process PDFs with worker pool
    if args['workers'] == 1:
        # Sequential processing
        for pdf_file in to_convert:
            worker_process_pdf(client, pdf_file, stats, 1)
    else:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=args['workers']) as executor:
            futures = {
                executor.submit(worker_process_pdf, client, pdf_file, stats, i % args['workers'] + 1): pdf_file
                for i, pdf_file in enumerate(to_convert)
            }

            for future in as_completed(futures):
                pdf_file = futures[future]
                try:
                    future.result()
                except Exception as e:
                    filename = os.path.basename(pdf_file)
                    stats.failed += 1
                    stats.errors.append((filename, str(e)))
                    if not verbose:
                        print(f"✗ Error processing {filename}: {e}")

    # Finish and print summary
    stats.finish()
    stats.print_summary(verbose)

    # Exit with appropriate code
    sys.exit(0 if stats.failed == 0 else 1)


if __name__ == "__main__":
    main()
