
from collections.abc import Callable
import os
import sys
from dotenv import load_dotenv
from string import Template
from datetime import datetime, date
import csv
from typing import Any, Iterator, List, get_args

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from libs.generic_helpers import get_filename_from_url

from pathlib import Path
import requests

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# from pydantic import BaseModel, Field
from typing import Literal
import json
from tools import *


import math

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET =  os.getenv('AI_DEVS_SECRET')
HUB_URL =  os.getenv('HUB_URL')
TASK =  os.getenv('TASK')
SOLUTION_URL =  os.getenv('SOLUTION_URL')
PEOPLE_URL =  os.getenv('SOURCE_URL1')
FIND_HIM_LOCATIONS_URL =  os.getenv('SOURCE_URL2')
DATA_FOLDER =  os.getenv('DATA_FOLDER')
TASK_NAME =  os.getenv('TASK_NAME')
ACCESS_LEVEL_POST_URL = os.getenv('POST_URL1')
LOCATION_POST_URL = os.getenv('POST_URL2')    

REWRITE_SUSPECTS = False

people_template = Template(PEOPLE_URL)
people_data_url = people_template.substitute(ai_devs_secret=AI_DEVS_SECRET)

findhim_locations_template = Template(FIND_HIM_LOCATIONS_URL)
findhim_locations_data_url = findhim_locations_template.substitute(ai_devs_secret=AI_DEVS_SECRET)

DATA_FILTERS = {
    'age': lambda x: x>=20 and x<=40,
    'birthPlace': lambda x: x.lower()=='grudziądz',
    'gender': lambda x: x.upper()=='M'
}


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
    
    file_name = get_filename_from_url(findhim_locations_data_url)
    findhim_locations_file = parent_folder / DATA_FOLDER / file_name
    findhim_locations_file.parent.mkdir(parents=True, exist_ok=True)
    if not findhim_locations_file.exists():
        r = requests.get(findhim_locations_data_url) 
        with open(findhim_locations_file, 'wb') as f:
            f.write(r.content)

    findhim_locations = json.loads(findhim_locations_file.read_text(encoding='utf-8'))

    cities_with_coordinates_file = parent_folder / DATA_FOLDER / 'cities_with_coordinates.json'
    if not cities_with_coordinates_file.exists():
        power_plants = findhim_locations['power_plants'].copy()
        cities_with_power_plants, _ = zip(*power_plants.items())

        cities_with_coordinatses = [ { city: {'longitude': get_coordinates(city).longitude, 'latitude':get_coordinates(city).latitude }} for city in cities_with_power_plants]

        with open(cities_with_coordinates_file, 'w', encoding='utf-8') as f:
            json.dump(cities_with_coordinatses, f)

    cities_with_coordinatses = json.loads(cities_with_coordinates_file.read_text(encoding='utf-8'))

    suspects_file = parent_folder / DATA_FOLDER / 'suspects.json'

    if REWRITE_SUSPECTS:
        
        file_name = get_filename_from_url(people_data_url)
        data_file = parent_folder / DATA_FOLDER / file_name
        data_file.parent.mkdir(parents=True, exist_ok=True)
        if not data_file.exists():
            r = requests.get(people_data_url) 
            with open(data_file, 'wb') as f:
                f.write(r.content)

        filtered_list = list(filter_data(read_csv_data(data_file), DATA_FILTERS))
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        structured_llm = llm.with_structured_output(JobTagClassifier)

        prompt = ChatPromptTemplate.from_messages([
        ("system",
        "You are job classification expert. Please assign tags to the job description fragment.\n"
        "Available tags: {tags}\n"
        "Return only the matching tags."),
        ("user", "Fragment: {input}")
        ])
        chain = prompt | structured_llm

        renamed_elements = [ {'name': elem['name'], 'surname': elem['surname'],'gender': elem['gender'], 'born': date.fromisoformat(elem['birthDate']).year, 'city': elem['birthPlace'],'job': elem['job']} for elem in [f.copy() for f in filtered_list]]

        for elem in renamed_elements:
            elem['tags'] = chain.invoke({"tags": ", ".join(TAGS), "input": elem['job']}).tags

        suspects = [elem for elem in renamed_elements if 'transport' in elem['tags']]
        

        with open(suspects_file, 'w', encoding='utf-8') as f:
            json.dump(suspects, f)

    with open(suspects_file, 'r', encoding='utf-8') as f:
        suspects = json.load(f)

    suspects = [{**elem, 'birthYear': elem['born']} for elem in suspects]

    # # TOOL
    # LOCATION_KEYS = {'name', 'surname'}
    # location_dict = {k: v for k, v in suspects[3].items() if k in LOCATION_KEYS}
    # location_dict["apikey"] = AI_DEVS_SECRET

    # response = requests.post(LOCATION_POST_URL, json=location_dict)

   
    # ACCESS_LEVEL_POST_URL
    # print(response.url)
    # print(' ')
    # print(suspects[3].__str__())
    # print(' ')
    # print(str(response.content))

    # TOOL
    # ACCESS_LEVEL_KEYS = {'name', 'surname', 'birthYear'}   
    # access_dict = {k: v for k, v in suspects[3].items() if k in ACCESS_LEVEL_KEYS}
    # access_dict["apikey"] = AI_DEVS_SECRET
    # response = requests.post(ACCESS_LEVEL_POST_URL, json=access_dict)

    # print(' ')
    # print(str(response.content))
    
    x = 1

    # ans["answer"] = [{'name': elem['name'], 'surname': elem['surname'],'gender': elem['gender'], 'born': elem['born'], 'city': elem['city'], 'tags': elem['tags']} for elem in answers]

    # response = requests.post(SOLUTION_URL, json=ans)

    # print(response.url)
    # print(str(response.content))

    # answer_file = parent_folder / DATA_FOLDER / 'answer.txt'

    # with open(answer_file, 'wb') as f:
    #     f.write(response.content)

    # openai_answer = completion.choices[0].message.content
    # ans_json = json.loads(openai_answer)



     

