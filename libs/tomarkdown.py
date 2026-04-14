
from pathlib import Path
import re
from html_to_markdown import convert, ConversionOptions, PreprocessingOptions
import requests
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_filename_from_url, save_file
load_dotenv()

def transform_html_to_markdown(output_dir: Path | str, html_url: str, preset: str = 'aggressive') -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    preprocessing = PreprocessingOptions(
        enabled=True,
        preset=preset,        # "minimal" | "standard" | "aggressive"
        remove_navigation=True,
        remove_forms=True,
    )

    filename = get_filename_from_url(html_url) if get_filename_from_url(html_url) else "output"
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

def extract_files_from_md(
    md_content: str,
    base_url: str = "",
    extensions: list[str] | None = None,
) -> list[dict]:
    results = []

    for line in md_content.splitlines():
        if re.match(r"^\|\s*-+", line) or "Name" in line:
            continue

        angle = re.findall(r"<([\w\-\.]+\.\w+)>", line)
        link  = re.findall(r"\[([^\[\]]+\.\w+)\]\(([^)]+)\)", line)

        candidates = []
        if angle:
            for name in angle:
                candidates.append((name, f"{base_url.rstrip('/')}/{name}" if base_url else name))
        elif link:
            for text, href in link:
                if "." in text and "Parent" not in text:
                    url = href if href.startswith("http") else f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                    candidates.append((text, url))

        for name, url in candidates:
            if extensions and Path(name).suffix.lower() not in extensions:
                continue
            results.append({"name": name, "url": url})

    return results

def download_files(
    files: list[dict],
    dest_dir: str = ".",
) -> list[Path]:
    """Pobiera pliki z listy zwróconej przez extract_files_from_md()."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    downloaded = []

    for f in files:
        try:
            r = requests.get(f["url"], timeout=30)
            r.raise_for_status()
            path = dest / f["name"]
            path.write_bytes(r.content)
            downloaded.append(path)
        except Exception as e:
            print(f"X {f['name']}: {e}")

    return downloaded