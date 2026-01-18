"""Valuation chart generation using matplotlib."""

import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


def _ensure_output_dir(output_dir: str) -> Path:
    """Ensure the output directory exists and return as Path."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_historical_multiple_chart(
    symbol: str,
    multiple_name: str,
    years: list,
    values: list,
    current_value: Optional[float] = None,
    stats: Optional[dict] = None,
    output_dir: str = "reports/charts",
) -> str:
    """
    Generate a historical multiple chart with max/median/min bands.

    Args:
        symbol: Stock ticker symbol
        multiple_name: Name of the multiple (e.g., "P/E", "P/FCF")
        years: List of years (strings or ints)
        values: List of multiple values corresponding to years
        current_value: Current TTM value (optional, for highlighting)
        stats: Dictionary with max, min, median statistics (optional)
        output_dir: Directory to save the chart

    Returns:
        Path to the saved chart PNG file.
    """
    output_path = _ensure_output_dir(output_dir)

    # Filter valid data points
    valid_data = [(y, v) for y, v in zip(years, values) if v is not None and v > 0]
    if not valid_data:
        return ""

    years_clean = [str(y) for y, _ in valid_data]
    values_clean = [v for _, v in valid_data]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot main line
    ax.plot(years_clean, values_clean, 'b-', linewidth=2, marker='o', markersize=4, label='Historical')

    # Plot statistics bands if provided
    if stats:
        max_val = stats.get("max")
        median_val = stats.get("median")
        min_val = stats.get("min")

        if max_val is not None:
            ax.axhline(y=max_val, color='green', linestyle='--', alpha=0.7, linewidth=1.5,
                       label=f'Max ({max_val:.1f}x)')
        if median_val is not None:
            ax.axhline(y=median_val, color='orange', linestyle='-', alpha=0.7, linewidth=1.5,
                       label=f'Median ({median_val:.1f}x)')
        if min_val is not None:
            ax.axhline(y=min_val, color='red', linestyle='--', alpha=0.7, linewidth=1.5,
                       label=f'Min ({min_val:.1f}x)')

    # Highlight current value if provided
    if current_value is not None and current_value > 0 and years_clean:
        ax.scatter([years_clean[-1]], [current_value], color='blue', s=150, zorder=5,
                   edgecolors='darkblue', linewidths=2, label=f'Current ({current_value:.1f}x)')

    # Styling
    ax.set_title(f'{symbol} Historical {multiple_name}', fontsize=14, fontweight='bold')
    ax.set_xlabel('Year', fontsize=11)
    ax.set_ylabel(f'{multiple_name} Multiple', fontsize=11)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Rotate x-axis labels if many years
    if len(years_clean) > 10:
        plt.xticks(rotation=45, ha='right')

    # Format y-axis
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1fx'))

    plt.tight_layout()

    # Save chart
    safe_multiple_name = multiple_name.replace("/", "_").replace(" ", "_")
    filename = f"{symbol}_{safe_multiple_name}_historical.png"
    filepath = output_path / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()

    return str(filepath)


def generate_peer_comparison_chart(
    target_symbol: str,
    target_name: str,
    target_value: float,
    peers: list,
    multiple_name: str,
    multiple_key: str,
    output_dir: str = "reports/charts",
) -> str:
    """
    Generate a combined peer comparison bar chart.

    Args:
        target_symbol: Target company ticker
        target_name: Target company name
        target_value: Target company's multiple value
        peers: List of peer dicts with 'symbol', 'name', and multiple value
        multiple_name: Display name of the multiple (e.g., "P/E Ratio")
        multiple_key: Key to extract from peer dicts (e.g., "peRatio")
        output_dir: Directory to save the chart

    Returns:
        Path to the saved chart PNG file.
    """
    output_path = _ensure_output_dir(output_dir)

    # Prepare data
    labels = [target_symbol]
    values = [target_value if target_value and target_value > 0 else 0]
    colors = ['#2196F3']  # Blue for target

    peer_values = []
    for peer in peers:
        peer_val = peer.get(multiple_key)
        if peer_val and peer_val > 0:
            labels.append(peer['symbol'])
            values.append(peer_val)
            colors.append('#9E9E9E')  # Gray for peers
            peer_values.append(peer_val)

    if len(values) < 2:
        return ""

    # Calculate peer average
    peer_avg = sum(peer_values) / len(peer_values) if peer_values else None

    # Create figure
    fig, ax = plt.subplots(figsize=(max(10, len(labels) * 1.2), 6))

    # Plot bars
    bars = ax.bar(labels, values, color=colors, edgecolor='darkgray', linewidth=0.5)

    # Add peer average line
    if peer_avg:
        ax.axhline(y=peer_avg, color='#FF9800', linestyle='--', linewidth=2,
                   label=f'Peer Avg ({peer_avg:.1f}x)')

    # Add value labels on bars
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    f'{val:.1f}x', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Styling
    ax.set_title(f'{target_symbol} vs Peers: {multiple_name}', fontsize=14, fontweight='bold')
    ax.set_xlabel('Company', fontsize=11)
    ax.set_ylabel(f'{multiple_name}', fontsize=11)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3, axis='y', linestyle='-', linewidth=0.5)

    # Rotate labels if many peers
    if len(labels) > 6:
        plt.xticks(rotation=45, ha='right')

    plt.tight_layout()

    # Save chart
    safe_multiple_name = multiple_name.replace("/", "_").replace(" ", "_")
    filename = f"{target_symbol}_{safe_multiple_name}_peer_comparison.png"
    filepath = output_path / filename
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()

    return str(filepath)


def generate_individual_peer_charts(
    target_symbol: str,
    target_value: float,
    peers: list,
    multiple_name: str,
    multiple_key: str,
    output_dir: str = "reports/charts",
) -> list:
    """
    Generate individual comparison charts for each peer vs target.

    Args:
        target_symbol: Target company ticker
        target_value: Target company's multiple value
        peers: List of peer dicts with 'symbol', 'name', and multiple value
        multiple_name: Display name of the multiple
        multiple_key: Key to extract from peer dicts
        output_dir: Directory to save charts

    Returns:
        List of paths to saved chart PNG files.
    """
    output_path = _ensure_output_dir(output_dir)
    chart_paths = []

    if not target_value or target_value <= 0:
        return chart_paths

    for peer in peers:
        peer_val = peer.get(multiple_key)
        if not peer_val or peer_val <= 0:
            continue

        peer_symbol = peer.get('symbol', 'PEER')
        peer_name = peer.get('name', peer_symbol)

        # Create figure
        fig, ax = plt.subplots(figsize=(6, 5))

        labels = [target_symbol, peer_symbol]
        values = [target_value, peer_val]

        # Color based on comparison
        if target_value < peer_val:
            colors = ['#4CAF50', '#9E9E9E']  # Green if target is cheaper
        elif target_value > peer_val:
            colors = ['#F44336', '#9E9E9E']  # Red if target is more expensive
        else:
            colors = ['#2196F3', '#9E9E9E']  # Blue if equal

        bars = ax.bar(labels, values, color=colors, edgecolor='darkgray', linewidth=0.5)

        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                    f'{val:.1f}x', ha='center', va='bottom', fontsize=10, fontweight='bold')

        # Calculate difference
        diff_pct = ((target_value - peer_val) / peer_val) * 100
        diff_text = f"{diff_pct:+.1f}%" if diff_pct != 0 else "Equal"

        ax.set_title(f'{target_symbol} vs {peer_symbol}\n{multiple_name} ({diff_text})',
                     fontsize=12, fontweight='bold')
        ax.set_ylabel(f'{multiple_name}', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y', linestyle='-', linewidth=0.5)

        plt.tight_layout()

        # Save chart
        safe_multiple_name = multiple_name.replace("/", "_").replace(" ", "_")
        filename = f"{target_symbol}_vs_{peer_symbol}_{safe_multiple_name}.png"
        filepath = output_path / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()

        chart_paths.append(str(filepath))

    return chart_paths
