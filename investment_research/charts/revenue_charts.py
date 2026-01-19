"""Revenue segment chart generation using matplotlib."""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


def _ensure_output_dir(output_dir: str) -> Path:
    """Ensure the output directory exists and return as Path."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _format_revenue(value: float) -> str:
    """Format revenue value with appropriate suffix (B/M/K)."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.0f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.0f}K"
    else:
        return f"${value:.0f}"


def _normalize_segment_data(raw_segments: list) -> list:
    """
    Normalize segment data from FMP API to flat format.

    FMP returns nested format like:
    [{"segment": "2025-03-31", "revenue": {"Cloud": 1000, "Commerce": 2000}}]

    We convert to:
    [{"segment": "Cloud", "revenue": 1000}, {"segment": "Commerce", "revenue": 2000}]
    """
    normalized = []

    for item in raw_segments:
        revenue_data = item.get('revenue')

        # If revenue is a dict (nested format), flatten it
        if isinstance(revenue_data, dict):
            for segment_name, revenue_value in revenue_data.items():
                if revenue_value and isinstance(revenue_value, (int, float)) and revenue_value > 0:
                    normalized.append({
                        "segment": segment_name,
                        "revenue": revenue_value
                    })
        # If revenue is a simple value, use segment field as name
        elif isinstance(revenue_data, (int, float)) and revenue_data > 0:
            segment_name = item.get('segment', 'Unknown')
            normalized.append({
                "segment": segment_name,
                "revenue": revenue_data
            })

    return normalized


def generate_product_segment_chart(
    symbol: str,
    company_name: str,
    product_segments: list,
    output_dir: str = "reports/charts",
) -> str:
    """
    Generate horizontal bar chart of revenue by product segment.

    Args:
        symbol: Stock ticker symbol
        company_name: Full company name
        product_segments: List of segment data from FMP API
        output_dir: Directory to save chart

    Returns:
        Path to saved chart PNG file, or empty string if no data.
    """
    if not product_segments:
        return ""

    output_path = _ensure_output_dir(output_dir)

    # Normalize the data format from FMP API
    normalized_segments = _normalize_segment_data(product_segments)

    if not normalized_segments:
        return ""

    # Sort by revenue descending
    sorted_segments = sorted(
        normalized_segments,
        key=lambda x: x.get('revenue', 0),
        reverse=True
    )

    # Limit to top 10 segments for readability
    if len(sorted_segments) > 10:
        sorted_segments = sorted_segments[:10]

    # Prepare data
    labels = [s['segment'][:35] for s in sorted_segments]  # Truncate long names
    values = [s['revenue'] for s in sorted_segments]
    total_revenue = sum(values)

    # Create figure with dynamic height
    fig_height = max(5, len(labels) * 0.6)
    fig, ax = plt.subplots(figsize=(10, fig_height))

    # Color palette - gradient from dark to light blue
    colors = plt.cm.Blues(np.linspace(0.8, 0.4, len(labels)))

    # Create horizontal bar chart
    y_pos = np.arange(len(labels))
    bars = ax.barh(y_pos, values, color=colors, edgecolor='darkgray', linewidth=0.5)

    # Add value labels
    max_val = max(values) if values else 1
    for bar, val in zip(bars, values):
        pct = (val / total_revenue) * 100 if total_revenue > 0 else 0
        label_text = f'{_format_revenue(val)} ({pct:.1f}%)'
        # Position label outside bar if bar is short
        if val < max_val * 0.3:
            ax.text(val + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                    label_text, ha='left', va='center', fontsize=9)
        else:
            ax.text(val - max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                    label_text, ha='right', va='center', fontsize=9, color='white',
                    fontweight='bold')

    # Styling
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()  # Largest at top
    ax.set_title(f'{symbol} Revenue by Product/Service Segment', fontsize=14,
                 fontweight='bold', pad=15)
    ax.set_xlabel('Revenue', fontsize=11)
    ax.grid(True, alpha=0.3, axis='x', linestyle='-', linewidth=0.5)

    # Remove y-axis spine for cleaner look
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    # Format x-axis
    def billions_formatter(x, pos):
        if x >= 1_000_000_000:
            return f'${x / 1_000_000_000:.0f}B'
        elif x >= 1_000_000:
            return f'${x / 1_000_000:.0f}M'
        else:
            return f'${x:,.0f}'

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(billions_formatter))

    plt.tight_layout()

    # Save chart
    filename = f"{symbol}_product_segments.png"
    filepath = output_path / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()

    return str(filepath)


def _normalize_geo_segment_data(raw_segments: list) -> list:
    """
    Normalize geographic segment data from FMP API to flat format.

    FMP may return nested format like:
    [{"region": "2025-03-31", "revenue": {"China": 1000, "USA": 2000}}]

    We convert to:
    [{"region": "China", "revenue": 1000}, {"region": "USA", "revenue": 2000}]
    """
    normalized = []

    for item in raw_segments:
        revenue_data = item.get('revenue')

        # If revenue is a dict (nested format), flatten it
        if isinstance(revenue_data, dict):
            for region_name, revenue_value in revenue_data.items():
                if revenue_value and isinstance(revenue_value, (int, float)) and revenue_value > 0:
                    normalized.append({
                        "region": region_name,
                        "revenue": revenue_value
                    })
        # If revenue is a simple value, use region field as name
        elif isinstance(revenue_data, (int, float)) and revenue_data > 0:
            region_name = item.get('region', 'Unknown')
            normalized.append({
                "region": region_name,
                "revenue": revenue_data
            })

    return normalized


def generate_geographic_segment_chart(
    symbol: str,
    company_name: str,
    geo_segments: list,
    output_dir: str = "reports/charts",
) -> str:
    """
    Generate pie chart of revenue by geographic region.

    Args:
        symbol: Stock ticker symbol
        company_name: Full company name
        geo_segments: List of geographic segment data from FMP API
        output_dir: Directory to save chart

    Returns:
        Path to saved chart PNG file, or empty string if no data.
    """
    if not geo_segments:
        return ""

    output_path = _ensure_output_dir(output_dir)

    # Normalize the data format from FMP API
    normalized_segments = _normalize_geo_segment_data(geo_segments)

    if not normalized_segments:
        return ""

    # Sort by revenue descending
    sorted_segments = sorted(
        normalized_segments,
        key=lambda x: x.get('revenue', 0),
        reverse=True
    )

    # Limit to top 8 regions, group rest as "Other"
    if len(sorted_segments) > 8:
        top_segments = sorted_segments[:7]
        other_revenue = sum(s['revenue'] for s in sorted_segments[7:])
        top_segments.append({"region": "Other", "revenue": other_revenue})
        sorted_segments = top_segments

    # Prepare data
    labels = [s['region'][:25] for s in sorted_segments]  # Truncate long names
    values = [s['revenue'] for s in sorted_segments]
    total_revenue = sum(values)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Color palette - use a nice blue gradient
    colors = plt.cm.Blues(np.linspace(0.3, 0.85, len(labels)))

    # Create pie chart with percentage labels
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,  # We'll add custom legend instead
        autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
        colors=colors,
        startangle=90,
        pctdistance=0.75,
        explode=[0.02] * len(values),
        wedgeprops={'edgecolor': 'white', 'linewidth': 1}
    )

    # Style the percentage labels
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_fontweight('bold')
        autotext.set_color('white')

    ax.set_title(f'{symbol} Revenue by Geography', fontsize=14, fontweight='bold', pad=20)

    # Add legend with revenue values
    legend_labels = [
        f'{label}: {_format_revenue(val)} ({val/total_revenue*100:.1f}%)'
        for label, val in zip(labels, values)
    ]
    ax.legend(
        wedges, legend_labels,
        title="Regions",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        fontsize=9
    )

    plt.tight_layout()

    # Save chart
    filename = f"{symbol}_geographic_segments.png"
    filepath = output_path / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()

    return str(filepath)
