
import logging
import math
import json
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Literal, get_args
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from pydantic import ConfigDict, Field, BaseModel
from dotenv import load_dotenv
import os
from langchain_core.callbacks import BaseCallbackHandler

import requests

load_dotenv()
AI_DEVS_SECRET = os.getenv('AI_DEVS_SECRET')
LOCATION_POST_URL = os.getenv('LOCATION_POST_URL')
DATA_FOLDER = os.getenv('DATA_FOLDER')
_SUSPECTS_FILE = Path(__file__).parent / DATA_FOLDER / 'suspects.json'
_POWER_PLANTS_FILE = Path(__file__).parent / DATA_FOLDER / 'findhim_locations.json'
_CITIES_COORDINATES_FILE = Path(__file__).parent / DATA_FOLDER / 'cities_with_coordinates.json'
ACCESS_LEVEL_POST_URL = os.getenv('POST_URL1')
LOCATION_POST_URL = os.getenv('POST_URL2')    

TagType = Literal['IT', 'transport', 'edukacja', 'medycyna', 'praca z ludźmi', 'praca z pojazdami', 'praca fizyczna']
TAGS: list[str] = list(get_args(TagType))

class JobTagClassifier(BaseModel):
    """Classify matching job tags based on job description (multiple tags possible)."""
    tags: List[TagType] = Field(..., description="List of tags related to job descibed in attached text fragment.")

class Coordinates(BaseModel):
    """Geographic coordinates of a location in decimal degrees."""
    # model_config = ConfigDict(extra="forbid")
    latitude: float = Field(..., description="Latitude in decimal degrees (e.g. 53.1325 for Białystok)")
    longitude: float = Field(..., description="Longitude in decimal degrees (e.g. 23.1688 for Białystok)")


@tool
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance in kilometers between two points 
    on Earth given their latitude and longitude in decimal degrees."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c

# Example: London (51.5074, -0.1278) to New York (40.7128, -74.0060)
# print(haversine(51.5074, -0.1278, 40.7128, -74.0060))  # ~5571 km

@tool
def obtain_suspects_locations(name: str, surname: str) -> list[dict]:
    """Fetch the list of geographic locations (latitude, longitude) visited by a suspect identified by name and surname."""
    location_dict = {'apikey': AI_DEVS_SECRET, 'name': name, 'surname': surname}
    response = requests.post(LOCATION_POST_URL, json=location_dict)
    return response.json()

@tool
def obtain_suspects_access_level(name: str, surname: str, birthYear: int) -> dict:
    """Fetch the access level of a suspect identified by name, surname and birth year.
    Returns a dict with keys: 'name', 'surname', 'accessLevel' (int)."""
    access_dict = {'apikey': AI_DEVS_SECRET, 'name': name, 'surname': surname, 'birthYear': birthYear}
    response = requests.post(ACCESS_LEVEL_POST_URL, json=access_dict)
    return response.json()

_suspects_cache: list[dict] | None = None

def _load_suspects_cache() -> list[dict]:
    global _suspects_cache
    if _suspects_cache is None:
        with open(_SUSPECTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _suspects_cache = [{**s, 'birthYear': s['born']} for s in data]
    return _suspects_cache

@tool
def get_suspects_count() -> int:
    """Return the total number of suspects in the dataset."""
    return len(_load_suspects_cache())

@tool
def get_suspect_by_index(index: int, fields: list[str] | None = None) -> dict:
    """Return a single suspect by index (0-based).
    Optionally filter returned fields by providing a list of field names.
    Available fields: name, surname, gender, born, birthYear, city, tags."""
    suspect = _load_suspects_cache()[index]
    if fields:
        return {k: v for k, v in suspect.items() if k in fields}
    return suspect


@tool
def get_power_plants() -> list[dict]:
    """Return the list of nuclear power plants with their city name, active status and power output.
    Each entry contains: city (str), is_active (bool), power (str), code (str)."""
    data = json.loads(_POWER_PLANTS_FILE.read_text(encoding='utf-8'))
    return [{'city': city, **info} for city, info in data['power_plants'].items()]


@tool
def get_cities_coordinates() -> list[dict]:
    """Return the list of cities with their geographic coordinates (latitude, longitude).
    Each entry contains: city (str), latitude (float), longitude (float)."""
    data = json.loads(_CITIES_COORDINATES_FILE.read_text(encoding='utf-8'))
    result = []
    for entry in data:
        for city, coords in entry.items():
            result.append({'city': city, 'latitude': coords['latitude'], 'longitude': coords['longitude']})
    return result


def get_coordinates(city: str) -> Coordinates:
    
    geocode_prompt = ChatPromptTemplate.from_messages([
        ("system",
        "You are a geography expert. Return precise latitude and longitude coordinates for the given city in Poland. "
        "Use decimal degrees format. Return only the coordinates, nothing else."),
        ("human", "What are the latitude and longitude of {city}, Poland?")
    ])

    llm = ChatOpenAI(model="gpt-5.2", temperature=0)
    geocode_chain = geocode_prompt | llm.with_structured_output(Coordinates)

    return geocode_chain.invoke({"city": city})

  # "gpt-5-mini"

class LoggerCallbackHandler(BaseCallbackHandler):
    def __init__(self, logger: logging.Logger):
        self.log = logger

    def on_tool_start(self, serialized, input_str, **kwargs):
        self.log.info(f"Tool call: {serialized['name']} | input: {input_str}")

    def on_tool_end(self, output, **kwargs):
        self.log.debug(f"Tool result: {output}")

    def on_tool_error(self, error, **kwargs):
        self.log.warning(f"Tool error: {error}")

    def on_agent_action(self, action, **kwargs):
        self.log.info(f"Agent action: {action.tool} | {action.tool_input}")

    def on_agent_finish(self, finish, **kwargs):
        self.log.info(f"Agent finished: {finish.return_values}")