
from typing import Tuple

import tiktoken
# gpt-5
# gpt-5-mini

def encode_prompt(prompt: str, model_name: str) -> Tuple[list[int], int]:
    '''Encodes the prompt using the specified model's tokenizer and 
    returns the list of token IDs and the token count.'''
    
    encoding_name = tiktoken.encoding_name_for_model(model_name)
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(prompt)
    return tokens, len(tokens)

# encoding = tiktoken.encoding_for_model("gpt-5-mini")
# tokens = encoding.encode("Twój tekst do policzenia")
# print(len(tokens)) 
