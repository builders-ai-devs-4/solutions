
from pathlib import Path
from html_to_markdown import convert, ConversionOptions, PreprocessingOptions
import requests
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_filename_from_url, save_file
load_dotenv()

def transform_html_to_markdown(output_dir: Path | str, html_url: str) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    preprocessing = PreprocessingOptions(
        enabled=True,
        preset="aggressive",        # "minimal" | "standard" | "aggressive"
        remove_navigation=True,
        remove_forms=True,
    )

    filename = get_filename_from_url(html_url)
    filename_md = Path(filename).stem + ".md"
    markdown_file_path = output_dir / filename_md

    response = requests.get(html_url)

    options = ConversionOptions(
        heading_style="atx",        # # H1 zamiast podkreślników
        strong_em_symbol="*",       # * zamiast _
        bullets="*+-",              # cykliczne znaki dla zagnieżdżonych list
        list_indent_width=2,        # wcięcie (dla Discord/Slack też działa)
        code_language="python",     # domyślny język dla bloków kodu
        escape_asterisks=True,
    )

    markdown = convert(response.text, options,  preprocessing=preprocessing)

    markdown_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(markdown_file_path, 'wb') as f:
        f.write(markdown.encode('utf-8'))

    return markdown_file_path