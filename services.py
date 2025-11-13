# services.py
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "smart_cook_ultra_simple_BIG.db")

def get_conn():
    # check_same_thread=False: erlaubt Nutzung in Streamlit
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def list_tables():
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        return [row[0] for row in cur.fetchall()]

def run_query(sql, params=()):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchall()
        return cols, rows

def search_recipes(q: str, limit: int = 20):
    sql = """
    SELECT id, title, servings
    FROM recipes
    WHERE title LIKE ?
    LIMIT ?
    """
    like = f"%{q}%"
    with get_conn() as con:
        cur = con.cursor()
        cur.execute(sql, (like, limit))
        cols = [c[0] for c in cur.description]
        return cols, cur.fetchall()