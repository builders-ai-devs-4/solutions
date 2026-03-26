from langchain_openai import ChatOpenAI # lub inny model, którego używasz
from langchain_core.prompts import ChatPromptTemplate

from modules.drone_model import DroneDocumentation


# 1. Wczytanie surowej dokumentacji Markdown
with open("drone.md", "r", encoding="utf-8") as file:
    raw_markdown = file.read()

# 2. Inicjalizacja modelu (musi obsługiwać structured output, np. gpt-4o, gpt-4o-mini)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 3. Wymuszenie na modelu użycia naszej struktury Pydantic
structured_llm = llm.with_structured_output(DroneDocumentation)

# 4. Przygotowanie promptu inżynieryjnego
prompt = ChatPromptTemplate.from_messages([
    ("system", """Jesteś doświadczonym inżynierem oprogramowania i technicznym pisarzem. 
    Twoim zadaniem jest przeanalizować surową dokumentację API z pliku Markdown.
    
    Wykonaj następujące kroki:
    1. Przeczytaj uważnie dokumentację.
    2. Wychwyć wszystkie informacje, napraw ewentualne niespójności językowe.
    3. Pogrupuj metody API według obszarów (np. 'Sterowanie silnikami', 'Kalibracja').
    4. Zwróć dane DOKŁADNIE w schemacie JSON, o który prosi użytkownik.
    Nie zmieniaj nazw metod ani ich parametrów, popraw jedynie jakość i strukturę opisu."""),
    ("user", "Oto surowa dokumentacja do przetworzenia:\n\n{dokumentacja}")
])

# 5. Połączenie promptu z modelem (Chain)
chain = prompt | structured_llm

print("Przetwarzanie dokumentacji przez LLM...")
# 6. Uruchomienie (wywołanie)
cleaned_docs = chain.invoke({"dokumentacja": raw_markdown})

# 7. Zapis do pliku JSON
with open("drone_api.json", "w", encoding="utf-8") as f:
    # Model_dump() zamienia obiekt Pydantic na słownik Pythona, który łatwo zapisać do JSON
    json.dump(cleaned_docs.model_dump(), f, ensure_ascii=False, indent=2)

print("Sukces! Zapisano ustrukturyzowaną i poprawioną dokumentację do drone_api.json")