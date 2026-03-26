import json
from pydantic import BaseModel, Field
from typing import List

# Definiujemy pojedynczą metodę
class ApiMethod(BaseModel):
    nazwa: str = Field(description="Nazwa metody, np. set(mode)")
    opis: str = Field(description="Opis działania metody i jej parametrów")
    przyklad: str = Field(description="Przykład użycia, np. set(engineON)")

# Definiujemy kategorię (np. Sterowanie silnikami, Konfiguracja)
class ApiCategory(BaseModel):
    nazwa_kategorii: str = Field(description="Nazwa obszaru/kategorii z tabeli")
    metody: List[ApiMethod] = Field(description="Lista metod należących do tej kategorii")

# Definiujemy główny dokument
class DroneDocumentation(BaseModel):
    urzadzenie: str = Field(description="Nazwa drona")
    producent: str = Field(description="Producent oprogramowania")
    informacje_ogolne: str = Field(description="Krótki opis, endpointy i wymagania requestu")
    kategorie_api: List[ApiCategory] = Field(description="Pogrupowane metody sterowania")
    cele_misji: List[str] = Field(description="Lista możliwych celów misji")
    przykłady_uzycia: str = Field(description="Krótkie podsumowanie przykładów użycia w formacie tekstowym")