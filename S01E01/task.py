
import os
import sys
from dotenv import load_dotenv
from string import Template
from datetime import datetime, date, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_filename_from_url


from pathlib import Path
import requests

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET =  os.getenv('AI_DEVS_SECRET')
HUB_URL =  os.getenv('HUB_URL')
TASK =  os.getenv('TASK')
SOLUTION_URL =  os.getenv('SOLUTION_URL')
SOURCE_URL =  os.getenv('SOURCE_URL')
DATA_FOLDER =  os.getenv('DATA_FOLDER')

t = Template(SOURCE_URL)
source_data_url = t.substitute(ai_devs_secret=AI_DEVS_SECRET)

DATA_FILTERS = {
    'age': lambda x: x>=20 and x<=40,
    'city': lambda x: x=='grudziądz',
    'gender': lambda x: x=='m'
}

TAGS = ['IT', 'transport', 'edukacja', 'medycyna', 
        'praca z ludźmi', 'praca z pojazdami', 'praca fizyczna']


FIXED_DATE = '2026-03-09'

current_folder = Path(__file__)
parent_folder = current_folder.parent

if __name__ == '__main__':

    file_name = get_filename_from_url(source_data_url)
    data_file = parent_folder / DATA_FOLDER / TASK / file_name
    data_file.parent.mkdir(parents=True, exist_ok=True)
    if not data_file.exists():
        r = requests.get(source_data_url) 
        with open(data_file, 'wb') as f:
            f.write(r.content)
    print(f"Data file is ready at: ")
