from typing import Tuple

import tiktoken

def encode_prompt(prompt: str, model_name: str) -> Tuple[list[int], int]:
    '''Encodes the prompt using the specified model's tokenizer and 
    returns the list of token IDs and the token count.'''
    
    encoding_name = tiktoken.encoding_name_for_model(model_name)
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(prompt)
    return tokens, len(tokens)