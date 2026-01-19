"""Emoji to LaTeX symbol substitution for XeLaTeX PDF generation."""

# Mapping of emojis to simple text/Unicode replacements
# We use simple Unicode characters that render well in most fonts
# instead of raw LaTeX commands (which conflict with pandoc's markdown processing)

EMOJI_TO_LATEX = {
    # Status indicators - use text markers that are clear
    "\U0001F7E2": "(+)",           # Green circle -> positive indicator
    "\U0001F7E1": "(~)",           # Yellow circle -> neutral indicator
    "\U0001F534": "(-)",           # Red circle -> negative indicator

    # Trend arrows - use Unicode arrows that fonts support
    "\u2197": "\u2191",            # Up-right arrow -> up arrow (Unicode)
    "\u2198": "\u2193",            # Down-right arrow -> down arrow (Unicode)
    "\u2192": "\u2192",            # Right arrow (keep as is)
    "\u2191": "\u2191",            # Up arrow (keep as is)
    "\u2193": "\u2193",            # Down arrow (keep as is)

    # Checkmarks and X marks - use Unicode
    "\u2705": "\u2713",            # White heavy check mark -> check mark
    "\u274C": "\u2717",            # Cross mark -> ballot X
    "\u2714": "\u2713",            # Heavy check mark -> check mark
    "\u2718": "\u2717",            # Heavy ballot X -> ballot X

    # Section header emojis - remove completely for clean PDF
    "\U0001F4CA": "",              # Bar chart
    "\U0001F4C8": "",              # Chart increasing
    "\U0001F4C9": "",              # Chart decreasing
    "\U0001F9E0": "",              # Brain
    "\U0001F402": "",              # Bull (ox)
    "\U0001F43B": "",              # Bear
    "\U0001F4CB": "",              # Clipboard
    "\U0001F3F0": "",              # Castle
    "\u26A0\uFE0F": "[!]",         # Warning sign
    "\u26A0": "[!]",               # Warning sign
    "\U0001F680": "",              # Rocket
    "\U0001F454": "",              # Necktie
    "\U0001F4B0": "$",             # Money bag
    "\U0001F4A1": "",              # Light bulb
    "\U0001F517": "",              # Link
    "\u2B50": "*",                 # Star
    "\u2B50\uFE0F": "*",           # Star with variation
    "\U0001F310": "",              # Globe
    "\U0001F3AF": "",              # Target
    "\U0001F4A5": "!",             # Collision
    "\U0001F30D": "",              # Globe Europe
    "\u2694\uFE0F": "",            # Crossed swords
    "\u2694": "",                  # Crossed swords
    "\U0001F9EE": "",              # Abacus
    "\U0001F9F2": "",              # Magnet
    "\U0001F3F7": "",              # Label
    "\U0001F9E9": "",              # Puzzle piece
    "\U0001F501": "",              # Repeat
    "\U0001F4E3": "",              # Megaphone
    "\U0001F91D": "",              # Handshake
    "\u2699\uFE0F": "",            # Gear
    "\u2699": "",                  # Gear
    "\u265F\uFE0F": "",            # Chess pawn
    "\u265F": "",                  # Chess pawn
    "\u2693": "",                  # Anchor
    "\U0001F4DA": "",              # Books
    "\U0001F4E6": "",              # Package
    "\U0001F9ED": "",              # Compass
    "\U0001F3E6": "$",             # Bank
    "\U0001F3A4": "",              # Microphone
    "\U0001F4B5": "$",             # Dollar banknote
    "\U0001F4BC": "",              # Briefcase

    # More common report emojis
    "\U0001F9ED": "",              # Compass
    "\U0001F4E2": "",              # Loudspeaker
    "\U0001F4DD": "",              # Memo
    "\U0001F4C4": "",              # Page facing up
    "\U0001F4C1": "",              # File folder
    "\U0001F4C2": "",              # Open file folder
    "\U0001F50D": "",              # Magnifying glass
    "\U0001F50E": "",              # Magnifying glass right
    "\U0001F4B1": "",              # Currency exchange
    "\U0001F4B2": "",              # Heavy dollar
    "\U0001F4B9": "",              # Chart yen

    # Phase indicators
    "\U0001F331": "",              # Seedling (Phase 1) -> remove
    "\U0001F4A8": "",              # Dash (Phase 2) -> remove
    "\u2696\uFE0F": "",            # Balance scale (Phase 3)
    "\u2696": "",                  # Balance scale
    "\U0001F4B8": "",              # Money with wings (Phase 4)

    # Medal/rating emojis
    "\U0001F947": "[1st]",         # Gold medal
    "\U0001F948": "[2nd]",         # Silver medal
    "\U0001F949": "[3rd]",         # Bronze medal
    "\U0001F3C6": "[*]",           # Trophy
    "\U0001F396\uFE0F": "*",       # Military medal
    "\U0001F396": "*",             # Military medal
    "\U0001F3C5": "*",             # Sports medal
    "\U0001F6E1\uFE0F": "",        # Shield -> remove
    "\U0001F6E1": "",              # Shield
    "\U0001F94E": "[N]",           # Narrow moat indicator
    "\U0001F94F": "[W]",           # Wide moat indicator
    "\U0001F925": "[N]",           # Narrow medal (silver-like)

    # Emoji skin tone and variation selectors (remove)
    "\uFE0F": "",                  # Variation selector-16

    # Additional emojis found in reports
    "\U0001F504": "",              # Counterclockwise arrows -> remove
    "\U0001F4E2": "",              # Loudspeaker -> remove
    "\U0001F4DD": "",              # Memo -> remove
    "\U0001F4C4": "",              # Page facing up -> remove
    "\U0001F4C1": "",              # File folder -> remove
    "\U0001F4C2": "",              # Open file folder -> remove
    "\U0001F50D": "",              # Magnifying glass -> remove
    "\U0001F50E": "",              # Magnifying glass right -> remove
    "\U0001F4B1": "",              # Currency exchange -> remove
    "\U0001F4B2": "",              # Heavy dollar sign -> remove
    "\U0001F4B9": "",              # Chart with upward trend and yen -> remove

    # Unicode symbols that may not render in Latin Modern
    "\u27A1": "->",                # Right arrow -> text
    "\u2713": "[Y]",               # Check mark -> text
    "\u2717": "[N]",               # X mark -> text
    "\u2714": "[Y]",               # Heavy check mark
    "\u2718": "[N]",               # Heavy X mark
    "\u25CF": "*",                 # Black circle -> asterisk
    "\u25CB": "o",                 # White circle -> o
    "\u25A0": "*",                 # Black square -> asterisk
    "\u25A1": "[]",                # White square -> brackets
}


def substitute_emojis(content: str) -> str:
    """
    Replace emojis with LaTeX-compatible symbols.

    Args:
        content: Markdown content potentially containing emojis

    Returns:
        Content with emojis replaced by LaTeX symbols
    """
    for emoji, latex in EMOJI_TO_LATEX.items():
        content = content.replace(emoji, latex)
    return content
