"""Base PDF generation utilities."""

import shutil
import subprocess


def check_pdf_dependencies():
    """
    Verify pandoc and xelatex are available.

    Returns:
        Tuple of (pandoc_path, xelatex_path)

    Raises:
        RuntimeError: If dependencies are not found
    """
    pandoc = shutil.which("pandoc")
    xelatex = shutil.which("xelatex")
    if not pandoc:
        raise RuntimeError("pandoc not found. Install in devcontainer: apt-get install pandoc")
    if not xelatex:
        raise RuntimeError("xelatex not found. Install in devcontainer: apt-get install texlive-xetex")
    return pandoc, xelatex


def md_to_pdf_pandoc(md_path: str, pdf_path: str, title: str = None) -> str:
    """
    Convert markdown to PDF using pandoc.

    Args:
        md_path: Path to the markdown file
        pdf_path: Path for the output PDF
        title: Optional title for the document

    Returns:
        Path to the generated PDF

    Raises:
        RuntimeError: If pandoc or xelatex are not found
        subprocess.CalledProcessError: If pandoc fails
    """
    check_pdf_dependencies()

    cmd = [
        "pandoc",
        md_path,
        "-o", pdf_path,
        "--pdf-engine=xelatex",
        "--toc",
        "--number-sections",
        "-V", "geometry:margin=1in",
        "-V", "fontsize=11pt",
    ]
    if title:
        cmd += ["-M", f"title={title}"]
    subprocess.run(cmd, check=True)
    return pdf_path
