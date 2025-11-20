import sqlite3

# Pfad zur Nachrichten-Datenbank
DB_PATH = "smart_cook_ultra_simple_BIG.db"


def init_db():
    """
    Legt die Tabelle 'messages' an, falls sie noch nicht existiert.
    Diese Tabelle speichert Chat-Nachrichten (user & assistant).
    """
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        con.commit()


def add_message(role: str, content: str):
    """
    Fügt eine Nachricht in die Tabelle 'messages' ein.
    """
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?);",
            (role, content),
        )
        con.commit()


def last_messages(limit: int = 5):
    """
    Gibt die letzten 'limit' Nachrichten als Liste von Dicts zurück.
    Neueste Nachricht kommt zuerst.
    """
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM messages ORDER BY id DESC LIMIT ?;",
            (limit,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
