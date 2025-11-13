from fastapi import FastAPI, HTTPException, Query
import sqlite3
from typing import List

# --- App erstellen ---
app = FastAPI(title="SmartCook Backend")

# --- Datenbankpfad ---
DB_PATH = "db.sqlite"

# --- Hilfsfunktion zum SQL-Abfragen ---
def query(sql: str, params: tuple = ()) -> list[dict]:
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def table_exists(name: str) -> bool:
    rows = query("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (name,))
    return bool(rows)

# --- Endpunkte ---
@app.get("/")
def home():
    return {"message": "SmartCook API läuft 🚀"}

@app.get("/tables")
def list_tables():
    return query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")

@app.get("/table/{name}")
def get_table(name: str, limit: int = 20):
    if not table_exists(name):
        raise HTTPException(404, f"Tabelle '{name}' nicht gefunden.")
    return query(f"SELECT * FROM {name} LIMIT ?;", (limit,))



# --- Rezepte anzeigen (wenn Tabelle existiert) ---
@app.get("/recipes")
def get_recipes(limit: int = 50):
    if not table_exists("recipes"):
        raise HTTPException(404, "Tabelle 'recipes' existiert nicht.")
    return query("SELECT * FROM recipes LIMIT ?;", (limit,))

# --- Zutaten anzeigen (wenn Tabelle existiert) ---
@app.get("/ingredients")
def get_ingredients(limit: int = 200):
    if not table_exists("ingredients"):
        raise HTTPException(404, "Tabelle 'ingredients' existiert nicht.")
    return query("SELECT * FROM ingredients LIMIT ?;", (limit,))

# --- Rezepte nach Zutaten suchen ---
@app.get("/recipes/search")
def search_recipes(
    ingredients: List[str] = Query(..., description="Zutaten als Parameter, z.B. ?ingredients=tomate&ingredients=reis"),
    limit: int = 20,
):
    # Prüfen ob Tabelle existiert
    if not table_exists("recipes"):
        raise HTTPException(404, "Tabelle 'recipes' existiert nicht.")

    # Prüfen ob die Spalte 'ingredients' in der Tabelle existiert
    columns = [c["name"] for c in query("PRAGMA table_info(recipes);")]
    if "ingredients" not in columns:
        raise HTTPException(400, "In der Tabelle 'recipes' gibt es keine Spalte 'ingredients'.")

    # SQL-Query vorbereiten: Zutaten mit AND suchen
    clauses = " AND ".join(["LOWER(ingredients) LIKE ?"] * len(ingredients))
    params = tuple([f"%{x.lower()}%" for x in ingredients])
    sql = f"SELECT * FROM recipes WHERE {clauses} LIMIT ?"
    return query(sql, params + (limit,))
