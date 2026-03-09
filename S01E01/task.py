
from collections.abc import Callable
import os
import sys
from dotenv import load_dotenv
from string import Template
from datetime import datetime, date, timedelta
import csv
from typing import Any, Iterator

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
    'birthPlace': lambda x: x.lower()=='grudziądz',
    'gender': lambda x: x.upper()=='M'
}
# name,surname,gender,birthDate,birthPlace,birthCountry,job

TAGS = ['IT', 'transport', 'edukacja', 'medycyna', 
        'praca z ludźmi', 'praca z pojazdami', 'praca fizyczna']


REF_DATE = '2026-03-09'

current_folder = Path(__file__)
parent_folder = current_folder.parent

FIXED_DATE = date.fromisoformat(REF_DATE) 

def count_age(birth_date: date, fixed_date: date = FIXED_DATE) -> int:
    """Calculates persons age based on fixed_date."""
    age = fixed_date.year - birth_date.year
    if (fixed_date.month, fixed_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age

def read_csv_data(csv_file: Path) -> Iterator[dict[str, Any]]:
    with csv_file.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            row = row.copy()  
            yield row

def filter_data(
    row_iter: Iterator[dict[str, Any]], 
    filters: dict[str, Callable[[Any], bool]],
) -> Iterator[dict[str, Any]]:
    for row in row_iter:
        row = row.copy()
        row['age'] = count_age(date.fromisoformat(row['birthDate']))
        
        if all(
            filters.get(column, lambda x: True)(row.get(column, '')) for column in filters
        ):
            yield row


if __name__ == '__main__':

    file_name = get_filename_from_url(source_data_url)
    data_file = parent_folder / DATA_FOLDER / file_name
    data_file.parent.mkdir(parents=True, exist_ok=True)
    if not data_file.exists():
        r = requests.get(source_data_url) 
        with open(data_file, 'wb') as f:
            f.write(r.content)

    results = list(filter_data(read_csv_data(data_file), DATA_FILTERS))
    s =1