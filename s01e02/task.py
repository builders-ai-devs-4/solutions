
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
from libs.logger import get_logger

from pathlib import Path
import requests

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent

from pydantic import BaseModel, Field
from typing import Literal

import json
from tools import *


import math


class InvestigationResult(BaseModel):
    """Final investigation result identifying the suspect near a nuclear power plant."""
    name: str = Field(..., description="First name of the suspect.")
    surname: str = Field(..., description="Surname of the suspect.")
    accessLevel: int = Field(..., description="Access level retrieved from the API.")
    powerPlant: str = Field(..., description="Power plant code in format PWR0000PL.")


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
MAX_AGENT_STEPS = 100

current_folder = Path(__file__)
parent_folder = current_folder.parent

logger = get_logger(TASK, log_dir=parent_folder / DATA_FOLDER/ "logs")


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

PROMPTS_DIR = parent_folder / "prompts"
system_prompt = (PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
user_prompt = (PROMPTS_DIR / "user.md").read_text(encoding="utf-8")

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
        llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

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

    tools = [haversine, obtain_suspects_locations, obtain_suspects_access_level, 
            get_suspects_count, get_suspect_by_index,
            get_power_plants, get_cities_coordinates]

    llm = ChatOpenAI(model="gpt-5-mini", temperature=0, max_retries=6)

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )

    config = {"configurable": {"thread_id": "1"}, "recursion_limit": MAX_AGENT_STEPS, "callbacks": [LoggerCallbackHandler(logger)]}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_prompt}]},
        config=config,
    )
    final_message = result["messages"][-1].content
    logger.info(f"Agent result: {final_message}")

    if "need more steps" in final_message.lower():
        raise RuntimeError(f"Agent ran out of steps (recursion_limit={MAX_AGENT_STEPS}). Increase MAX_AGENT_STEPS.")

    structured_llm = ChatOpenAI(model="gpt-5-mini", temperature=0).with_structured_output(InvestigationResult)
    investigation_result: InvestigationResult = structured_llm.invoke(
        f"Extract the investigation findings from this agent report:\n{final_message}"
    )
    logger.info(f"Structured result: {investigation_result}")

    ans = {
        "apikey": AI_DEVS_SECRET,
        "task": TASK_NAME,
        "answer": {
            "name": investigation_result.name,
            "surname": investigation_result.surname,
            "accessLevel": investigation_result.accessLevel,
            "powerPlant": investigation_result.powerPlant,
        }
    }
    logger.info(f"Sending answer: {ans}")
    response = requests.post(SOLUTION_URL, json=ans)
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response body: {response.text}")
    print(response.text)
    
    answer_file = parent_folder / DATA_FOLDER / 'answer.txt'

    with open(answer_file, 'wb') as f:
        f.write(response.content)



     

