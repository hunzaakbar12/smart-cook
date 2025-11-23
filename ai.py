import sqlite3
from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.6)

AI_STYLE_PROMPT = """
Du bist SmartCook, ein freundlicher Kochassistent.

REGELN:
- Hauptquelle sind die Rezeptdaten.
- Wenn etwas nicht in den Daten steht, DARFST du deine eigene Meinung sagen
  basierend auf allgemeinem Kochwissen.
- Du darfst Tipps geben wie:
  * "Brokkoli passt gut dazu"
  * "Brate ihn vorher an"
  * "Achte auf die Konsistenz"
- KEINE komplett neuen Rezepte erfinden.

ZIEL:
Hilf der Person wirklich beim Kochen.
Sei locker, freundlich und praktisch.
"""

def load_all_recipes(db_path: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM recipes")
    rows = cur.fetchall()
    conn.close()
    return rows

def build_recipe_list(rows):
    return "\n".join(f"- {r[1]}" for r in rows)

main_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Hier sind die gespeicherten Rezepte:

{recipes_block}

Benutzerfrage:
\"\"\"{user_query}\"\"\"

Antworte:
- basierend auf den Daten
- mit sinnvollen Tipps aus deiner Erfahrung
"""
)

main_chain = main_prompt | llm | StrOutputParser()

def handle_user_query(db_path: str, query: str) -> str:
    rows = load_all_recipes(db_path)
    recipes_block = build_recipe_list(rows)
    return main_chain.invoke({"user_query": query, "recipes_block": recipes_block}).strip()
