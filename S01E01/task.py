
import os
from dotenv import load_dotenv
from string import Template

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AI_DEVS_SECRET =  os.getenv('AI_DEVS_SECRET')
HUB_URL =  os.getenv('HUB_URL')
TASK =  os.getenv('TASK')
SOLUTION_URL =  os.getenv('SOLUTION_URL')
SOURCE_URL =  os.getenv('SOURCE_URL')

t = Template(SOURCE_URL)
source_data_url = t.substitute(ai_devs_secret=AI_DEVS_SECRET)

DATA_FILTERS = {
    'age': lambda x: x>=20 and x<=40,
    'city': lambda x: x=='grudziądz',
    'gender': lambda x: x=='m'
}