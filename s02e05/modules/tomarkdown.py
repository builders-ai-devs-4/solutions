
from pathlib import Path
from html_to_markdown import convert, ConversionOptions, PreprocessingOptions
import requests
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_filename_from_url, save_file
load_dotenv()

DRONE_DOCS_URL = os.getenv('SOURCE_URL2')
TASK           = os.getenv('TASK')
DATA_FOLDER    = os.getenv('DATA_FOLDER')
TASK_NAME      = os.getenv('TASK_NAME')

current_folder = Path(__file__)
parent_folder_path  = current_folder.parent
date_folder_path = parent_folder_path / DATA_FOLDER
task_data_folder = parent_folder_path / DATA_FOLDER / TASK_NAME

preprocessing = PreprocessingOptions(
    enabled=True,
    preset="aggressive",        # "minimal" | "standard" | "aggressive"
    remove_navigation=True,
    remove_forms=True,
)

filename = get_filename_from_url(DRONE_DOCS_URL)
filename_md = Path(filename).stem + ".md"
markdown_file_path = task_data_folder / filename_md

response = requests.get(DRONE_DOCS_URL)

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