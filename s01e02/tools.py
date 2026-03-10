
import math
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Literal, get_args
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from pydantic import ConfigDict, Field, BaseModel

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