"""
PDF to Markdown processor using PaddleOCR PP-StructureV3.

This module handles the conversion of PDF files to Markdown format
using PaddleOCR's document parsing capabilities.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Suppress PaddleOCR verbose logging
logging.getLogger('ppocr').setLevel(logging.WARNING)
logging.getLogger('paddle').setLevel(logging.WARNING)

try:
    from paddleocr import PPStructure
except ImportError:
    PPStructure = None

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF to Markdown conversion using PaddleOCR."""

    def __init__(self, config: Dict):
        """
        Initialize the PDF processor.

        Args:
            config: Configuration dict with settings:
                - device: "cpu" or "gpu" (default: "cpu")
                - lang: Language code (default: "en")
                - use_gpu: Boolean for GPU usage (default: False)
                - model_name: Model variant (default: "PP-DocLayout_plus-L")
        """
        if PPStructure is None:
            raise ImportError(
                "PaddleOCR not installed. Install with: "
                "pip install paddleocr"
            )

        self.config = config
        device = "gpu" if config.get("use_gpu", False) else "cpu"
        lang = config.get("lang", "en")

        logger.info(f"Initializing PaddleOCR with device={device}, lang={lang}")

        try:
            # PPStructure in PaddleOCR 2.8.1 uses different parameters
            self.pipeline = PPStructure(
                lang=lang,
                use_gpu=config.get("use_gpu", False),
                show_log=False,  # Disable verbose debug output
                table=True,            # Enable table recognition
                structure_version='PP-StructureV2'  # Use structure version 2
            )
            logger.info("PaddleOCR pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def process_pdf(self, pdf_data: bytes, output_dir: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Convert PDF bytes to Markdown.

        Args:
            pdf_data: PDF file as bytes
            output_dir: Optional directory to save extracted images

        Returns:
            Tuple of (markdown_text, list_of_image_paths)

        Raises:
            Exception: If processing fails
        """
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            tmp_pdf.write(pdf_data)
            tmp_pdf_path = tmp_pdf.name

        try:
            logger.info(f"Processing PDF from temporary file: {tmp_pdf_path}")

            # Process PDF with PaddleOCR PPStructure
            # Note: PPStructure in 2.8.1 returns different format
            logger.info(f"Starting PDF processing...")
            result = self.pipeline(tmp_pdf_path)

            # Get total pages for progress tracking
            total_pages = len(result)
            logger.info(f"Processing {total_pages} pages...")

            # Convert results to markdown format
            markdown_parts = []
            image_paths = []

            # Progress tracking variables
            last_reported_progress = 0

            # PPStructure returns a list of dictionaries
            for idx, page_result in enumerate(result, 1):
                # Report progress every 10% or every 10 pages (whichever is smaller)
                progress = int((idx / total_pages) * 100)
                if progress >= last_reported_progress + 10 or idx % 10 == 0:
                    logger.info(f"Processing progress: {idx}/{total_pages} pages ({progress}%)")
                    last_reported_progress = progress
                # Each page_result can be a dict or contain multiple elements
                if isinstance(page_result, dict):
                    res_list = [page_result]
                elif isinstance(page_result, list):
                    res_list = page_result
                else:
                    continue

                for res in res_list:
                    if isinstance(res, dict):
                        res_type = res.get('type', '')

                        if res_type == 'text':
                            # Extract text content
                            text = res.get('res', '')
                            if isinstance(text, dict):
                                text = text.get('text', '')
                            elif isinstance(text, list):
                                # Handle case where text is a list of OCR results
                                text_items = []
                                for item in text:
                                    if isinstance(item, dict):
                                        text_items.append(item.get('text', ''))
                                    elif isinstance(item, list) and len(item) >= 2:
                                        # Handle OCR result format [[text, confidence], ...]
                                        text_items.append(str(item[0]) if item[0] else '')
                                    else:
                                        text_items.append(str(item))
                                text = ' '.join(filter(None, text_items))
                            if text:
                                # Ensure text is a string before appending
                                markdown_parts.append(str(text))
                        elif res_type == 'table':
                            # Extract table as HTML
                            table_res = res.get('res', {})
                            if isinstance(table_res, dict):
                                html_table = table_res.get('html', '')
                            else:
                                html_table = str(table_res)
                            if html_table:
                                markdown_parts.append(f"\n{html_table}\n")
                        elif res_type == 'figure':
                            # Handle figures/images
                            img_res = res.get('res', {})
                            if isinstance(img_res, dict):
                                img_path = img_res.get('img_path', '')
                                if img_path and output_dir:
                                    image_paths.append(img_path)
                                    markdown_parts.append(f"\n![Figure {idx}]({img_path})\n")

            # Join all markdown parts (ensuring all are strings)
            markdown_text = '\n'.join(str(part) for part in markdown_parts)

            logger.info(f"✓ Successfully converted PDF ({total_pages} pages processed, {len(markdown_text)} characters)")
            return markdown_text, image_paths

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_pdf_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_pdf_path}: {e}")

    def process_pdf_file(self, pdf_path: str, output_md_path: Optional[str] = None) -> str:
        """
        Process a PDF file and optionally save the output.

        Args:
            pdf_path: Path to input PDF file
            output_md_path: Optional path to save markdown output

        Returns:
            Markdown text
        """
        logger.info(f"Processing PDF file: {pdf_path}")

        # Read PDF file
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        # Determine output directory for images
        if output_md_path:
            output_dir = str(Path(output_md_path).parent / "images")
        else:
            output_dir = None

        # Process PDF
        markdown_text, image_paths = self.process_pdf(pdf_data, output_dir)

        # Save markdown if output path specified
        if output_md_path:
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(markdown_text)
            logger.info(f"Saved markdown to: {output_md_path}")

            if image_paths:
                logger.info(f"Saved {len(image_paths)} images to: {output_dir}")

        return markdown_text


def test_processor():
    """Test function for local development."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_processor.py <pdf_file>")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)

    pdf_path = sys.argv[1]
    output_path = pdf_path.replace(".pdf", ".md")

    config = {
        "use_gpu": False,
        "lang": "en"
    }

    processor = PDFProcessor(config)
    processor.process_pdf_file(pdf_path, output_path)
    print(f"Conversion complete: {output_path}")


if __name__ == "__main__":
    test_processor()
