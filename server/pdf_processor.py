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
                show_log=True,
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
            result = self.pipeline(tmp_pdf_path)

            # Convert results to markdown format
            markdown_parts = []
            image_paths = []

            for idx, res in enumerate(result):
                if res.get('type', '') == 'text':
                    # Extract text content
                    text = res.get('res', {}).get('text', '')
                    if text:
                        markdown_parts.append(text)
                elif res.get('type', '') == 'table':
                    # Extract table as HTML and convert to markdown table format
                    html_table = res.get('res', {}).get('html', '')
                    if html_table:
                        markdown_parts.append(f"\n{html_table}\n")
                elif res.get('type', '') == 'figure':
                    # Handle figures/images
                    img_path = res.get('res', {}).get('img_path', '')
                    if img_path and output_dir:
                        output_path = Path(output_dir)
                        output_path.mkdir(parents=True, exist_ok=True)
                        # Copy or save image to output directory
                        image_paths.append(img_path)
                        markdown_parts.append(f"\n![Figure {idx}]({img_path})\n")

            # Join all markdown parts
            markdown_text = '\n'.join(markdown_parts)

            logger.info(f"Successfully converted PDF to Markdown ({len(result)} elements processed)")
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
