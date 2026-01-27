from rich.console import Console
from rich.text import Text
import pyfiglet
import random

def print_banner():
    """Renders a colorful banner using a random font."""
    console = Console()
    
    # Curated list of readable and well-sized fonts
    curated_fonts = [
        "slant", "standard", "doom", "big", "small", 
        "cybermedium", "smslant", "block", "digital", 
        "shadow", "speed", "lean", "mini", "script",
        "ivrit", "computer"
    ]
    
    font = random.choice(curated_fonts)
    
    try:
        ascii_art = pyfiglet.figlet_format("Mah Framework", font=font)
    except Exception:
        ascii_art = pyfiglet.figlet_format("Mah Framework", font="slant")
        font = "slant (fallback)"

    # Create a Rich Text object
    rich_text = Text()
    
    # Colors for the rainbow
    colors = [
        "#FF0000", "#FF7F00", "#FFFF00", "#00FF00", 
        "#0000FF", "#4B0082", "#9400D3"
    ]
    
    lines = ascii_art.splitlines()
    for i, line in enumerate(lines):
        for j, char in enumerate(line):
            # Calculate color index based on position to create a diagonal gradient
            color_index = int((i + j / 2) / 4) % len(colors)
            rich_text.append(char, style=colors[color_index])
        rich_text.append("\n")
        
    console.print(rich_text)
