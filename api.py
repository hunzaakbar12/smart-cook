from fastapi import FastAPI, HTTPException, Query
from typing import List
import sqlite3

# Import deiner Chat-DB-Funktionen
from chat_db import init_db, add_message, last_messages

# Import der KI-Funktion deiner Freundin
from ai import handle_user_query

# Pfad zur großen Rezept-Datenbank
DB_PATH = "smart_cook_ultra_simple_BIG.db"

# FastAPI App erstellen
app = FastAPI(title="SmartCook Backend")

# -------------------------------------------------------
# Datenbank initialisieren (messages-Tabelle)
# -------------------------------------------------------
@app.on_event("startup")
def startup_event():
    init_db()


# -------------------------------------------------------
# Hilfsfunktion für einfache SQL-Abfragen
# -------------------------------------------------------
def query(sql: str, params: tuple = ()) -> list[dict]:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def table_exists(name: str) -> bool:
    rows = query("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (name,))
    return bool(rows)


# -------------------------------------------------------
# Basis-Endpunkt
# -------------------------------------------------------
@app.get("/")
def home():
    return {"message": "SmartCook API läuft 🚀"}


# -------------------------------------------------------
# Tabellen-Endpunkte (Rezepte, Zutaten, Suche)
# -------------------------------------------------------
@app.get("/tables")
def list_tables():
    return query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")


@app.get("/table/{name}")
def get_table(name: str, limit: int = 20):
    if not table_exists(name):
        raise HTTPException(404, f"Tabelle '{name}' nicht gefunden.")
    return query(f"SELECT * FROM {name} LIMIT ?;", (limit,))


@app.get("/recipes")
def get_recipes(limit: int = 50):
    if not table_exists("recipes"):
        raise HTTPException(404, "Tabelle 'recipes' existiert nicht.")
    return query("SELECT * FROM recipes LIMIT ?;", (limit,))


@app.get("/ingredients")
def get_ingredients(limit: int = 200):
    if not table_exists("ingredients"):
        raise HTTPException(404, "Tabelle 'ingredients' existiert nicht.")
    return query("SELECT * FROM ingredients LIMIT ?;", (limit,))


@app.get("/recipes/search")
def search_recipes(
    ingredients: List[str] = Query(...),
    limit: int = 20,
):
    if not table_exists("recipes"):
        raise HTTPException(404, "Tabelle 'recipes' existiert nicht.")

    columns = [c["name"] for c in query("PRAGMA table_info(recipes);")]
    if "ingredients" not in columns:
        raise HTTPException(400, "Spalte 'ingredients' existiert nicht.")

    clauses = " AND ".join(["LOWER(ingredients) LIKE ?"] * len(ingredients))
    params = tuple([f"%{x.lower()}%" for x in ingredients])
    sql = f"SELECT * FROM recipes WHERE {clauses} LIMIT ?"

    return query(sql, params + (limit,))


# -------------------------------------------------------
# Chat-Verlauf
# -------------------------------------------------------
@app.get("/history")
def history(limit: int = 10):
    return last_messages(limit)


# -------------------------------------------------------
# KI-Chat-Endpunkt – HIER passiert die Integration
# -------------------------------------------------------
@app.post("/chat")
def chat(prompt: str):
    """
    1. User-Nachricht speichern
    2. KI-Antwort über handle_user_query() holen
    3. Assistant-Nachricht speichern
    4. Antwort ans Frontend zurückgeben
    """
    # 1. speichern
    add_message("user", prompt)

    # 2. KI-Antwort holen (aus ai.py)
    answer = handle_user_query(DB_PATH, prompt)

    # 3. speichern
    add_message("assistant", answer)

    # 4. zurückgeben
    return {"answer": answer}

