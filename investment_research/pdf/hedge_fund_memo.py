"""Hedge fund investment memo PDF generation."""

import os
import subprocess
from datetime import datetime
from pathlib import Path

from .base import check_pdf_dependencies
from .emoji_substitution import substitute_emojis


def generate_hedge_fund_memo_pdf(
    ticker: str,
    company_name: str,
    task_outputs: list,
    section_names: list,
    output_path: str
) -> str:
    """
    Generate a concise hedge fund investment memo style PDF.
    Features: Executive summary, thesis-driven, bull/bear cases prominent.

    Args:
        ticker: Stock ticker symbol
        company_name: Full company name
        task_outputs: List of CrewAI task output objects
        section_names: List of section names corresponding to task outputs
        output_path: Path for the output PDF

    Returns:
        Path to the generated PDF

    Raises:
        RuntimeError: If pandoc or xelatex are not found
        subprocess.CalledProcessError: If pandoc fails
    """
    check_pdf_dependencies()

    temp_md = output_path.replace('.pdf', '_memo_temp.md')
    report_date = datetime.utcnow().strftime("%B %d, %Y")

    # Extract key sections for reorganization
    sections_dict = {}
    for i, task_output in enumerate(task_outputs):
        name = section_names[i] if i < len(section_names) else f"Section {i+1}"
        content = task_output.raw.strip()

        # Replace --- separators with *** to avoid YAML parsing issues in pandoc
        lines = content.split('\n')
        processed_lines = []
        for line in lines:
            if line.strip() == '---':
                processed_lines.append('***')
            else:
                processed_lines.append(line)
        content = '\n'.join(processed_lines)

        # Substitute emojis with LaTeX-compatible symbols
        content = substitute_emojis(content)

        # Normalize chart paths
        content = content.replace('./reports/charts/', 'reports/charts/')

        sections_dict[name] = content

    with open(temp_md, "w", encoding="utf-8") as f:
        f.write(f"""---
title: "Investment Memo"
subtitle: "{ticker} | {company_name}"
date: "{report_date}"
geometry: margin=1in
fontsize: 11pt
header-includes:
  - \\usepackage{{fancyhdr}}
  - \\usepackage{{xcolor}}
  - \\usepackage{{colortbl}}
  - \\usepackage{{booktabs}}
  - \\usepackage{{graphicx}}
  - \\usepackage{{array}}
  - \\usepackage{{titlesec}}
  - \\usepackage{{parskip}}
  - \\usepackage{{amssymb}}
  - \\definecolor{{darkgreen}}{{RGB}}{{0,100,0}}
  - \\definecolor{{darkred}}{{RGB}}{{139,0,0}}
  - \\definecolor{{lightgray}}{{RGB}}{{245,245,245}}
  - \\definecolor{{ForestGreen}}{{RGB}}{{34,139,34}}
  - \\definecolor{{Orange}}{{RGB}}{{255,165,0}}
  - \\definecolor{{Red}}{{RGB}}{{220,20,60}}
  - \\rowcolors{{2}}{{lightgray!15}}{{white}}
  - \\titlespacing*{{\\section}}{{0pt}}{{2ex plus 1ex minus .2ex}}{{1.5ex plus .2ex}}
  - \\titlespacing*{{\\subsection}}{{0pt}}{{1.5ex plus 1ex minus .2ex}}{{1ex plus .2ex}}
  - \\setlength{{\\parskip}}{{0.6em}}
  - \\pagestyle{{fancy}}
  - \\fancyhead[L]{{\\textbf{{INVESTMENT MEMO}}}}
  - \\fancyhead[R]{{{ticker}}}
  - \\fancyfoot[C]{{\\thepage}}
  - \\fancyfoot[L]{{CONFIDENTIAL}}
---

\\begin{{center}}
\\LARGE\\textbf{{INVESTMENT MEMO}}

\\vspace{{0.3cm}}

\\Large\\textbf{{{ticker}}} | {company_name}

\\vspace{{0.2cm}}

\\normalsize {report_date}
\\end{{center}}

\\vspace{{0.5cm}}

***

""")

        # Executive Summary / Business Profile first
        if "BUSINESS PROFILE" in sections_dict:
            f.write("# Executive Summary\n\n")
            f.write(sections_dict["BUSINESS PROFILE"] + "\n\n")
            f.write("\\newpage\n\n")

        # Business Phase (Investment Stage)
        if "BUSINESS PHASE" in sections_dict:
            f.write("# Investment Stage Analysis\n\n")
            f.write(sections_dict["BUSINESS PHASE"] + "\n\n")
            f.write("\\newpage\n\n")

        # Price & Sentiment (includes Bull/Bear cases)
        if "PRICE & SENTIMENT" in sections_dict:
            f.write("# Market Sentiment & Catalysts\n\n")
            f.write(sections_dict["PRICE & SENTIMENT"] + "\n\n")
            f.write("\\newpage\n\n")

        # Moat Analysis
        if "BUSINESS & MOAT" in sections_dict:
            f.write("# Competitive Position & Moat\n\n")
            f.write(sections_dict["BUSINESS & MOAT"] + "\n\n")
            f.write("\\newpage\n\n")

        # Key Metrics
        if "KEY METRICS" in sections_dict:
            f.write("# Key Metrics\n\n")
            f.write(sections_dict["KEY METRICS"] + "\n\n")
            f.write("\\newpage\n\n")

        # Execution Risk
        if "EXECUTION RISK" in sections_dict:
            f.write("# Execution Risk\n\n")
            f.write(sections_dict["EXECUTION RISK"] + "\n\n")
            f.write("\\newpage\n\n")

        # Growth Drivers
        if "GROWTH DRIVERS" in sections_dict:
            f.write("# Growth Drivers\n\n")
            f.write(sections_dict["GROWTH DRIVERS"] + "\n\n")
            f.write("\\newpage\n\n")

        # Management Quality (was "MANAGEMENT & RISK")
        if "MANAGEMENT QUALITY" in sections_dict:
            f.write("# Management Quality & Risks\n\n")
            f.write(sections_dict["MANAGEMENT QUALITY"] + "\n\n")
            f.write("\\newpage\n\n")

        # Valuation (was "QUANT & VALUATION")
        if "VALUATION" in sections_dict:
            f.write("# Valuation & Financials\n\n")
            f.write(sections_dict["VALUATION"] + "\n\n")
            f.write("\\newpage\n\n")

        # Investment Scorecard
        if "INVESTMENT SCORECARD" in sections_dict:
            f.write("# Investment Scorecard\n\n")
            f.write(sections_dict["INVESTMENT SCORECARD"] + "\n\n")

        # Disclaimer
        f.write("""

\\vspace{0.5cm}

\\begin{center}
\\small\\textit{This memo was generated by an AI investment research system for informational purposes only. Not investment advice.}
\\end{center}
""")

    # Determine resource path for images (charts directory)
    output_dir = Path(output_path).parent
    resource_paths = [
        str(output_dir),
        str(output_dir / "charts"),
        "reports/charts",
        ".",
    ]
    resource_path = ":".join(resource_paths)

    # Generate PDF
    cmd = [
        "pandoc", temp_md,
        "-o", output_path,
        "--pdf-engine=xelatex",
        "-V", "documentclass=article",
        "-V", "colorlinks=true",
        f"--resource-path={resource_path}",
    ]
    subprocess.run(cmd, check=True)

    # Clean up temp file
    if os.path.exists(temp_md):
        os.remove(temp_md)

    return output_path
