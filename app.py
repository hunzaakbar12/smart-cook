from ai import handle_user_query   # <-- deine KI-Funktion

import streamlit as st
import sqlite3
import pandas as pd

# ---- App-Konfiguration ----
st.set_page_config(page_title="Smart Cook", page_icon="🤖", layout="wide")

# ---- Header ----
st.title("🤖 Smart Cook – Dein KI-Rezept-Guide")
st.caption("Frag nach Rezepten oder Zutaten – ich finde passende Ideen in deiner Datenbank :)")

# ---- Sidebar: Einstellungen & Verbindung ----
st.sidebar.header("Settings")
st.sidebar.write("This is a simple chat application using SQLite. Connect to the database and start chatting.")

db_path = st.sidebar.text_input("Database", value="smart_cook_ultra_simple_BIG.db")

# Verbindung herstellen
if st.sidebar.button("Connect"):
    try:
        conn = sqlite3.connect(db_path)
        st.session_state["db_connected"] = True
        st.session_state["db_path"] = db_path
        st.sidebar.success("✅ Connected successfully!")
    except Exception as e:
        st.session_state["db_connected"] = False
        st.sidebar.error(f"❌ Connection failed: {e}")

# ---- Funktion: Zubereitungsschritte laden ----
def get_recipe_steps(db_path, recipe_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT step_no, instruction
        FROM recipe_steps
        WHERE recipe_id = ?
        ORDER BY step_no;
    """, (recipe_id,))
    steps = cur.fetchall()
    conn.close()
    return steps

# ---- Schnellsuche ----
st.sidebar.divider()
st.sidebar.subheader("Schnelle Suche")
q = st.sidebar.text_input("Suchwörter (Titel oder Rezepte)", placeholder="z.B. Rezepte, Zutaten ...")
top_n = st.sidebar.slider("Anzahl der Ergebnisse", 1, 10)

# ---- Hauptbereich ----
st.subheader("Ergebnisse")

if st.session_state.get("db_connected", False):
    if q.strip():
        try:
            conn = sqlite3.connect(st.session_state["db_path"])
            cur = conn.cursor()

            sql = """
                SELECT DISTINCT r.id, r.title AS recipe_title, r.servings
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                LEFT JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE r.title LIKE ? OR i.name LIKE ?
                LIMIT ?;
            """

            like_q = f"%{q}%"
            cur.execute(sql, (like_q, like_q, top_n))
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            conn.close()

            if rows:
                df = pd.DataFrame(rows, columns=cols)
                for _, row in df.iterrows():
                    with st.expander(f"🍽️ {row['recipe_title']}"):

                        # --- Portionen anzeigen ---
                        st.write(f"**Portionen:** {row['servings']}")

                        # --- Neue Funktion: Schritte laden ---
                        steps = get_recipe_steps(st.session_state["db_path"], int(row["id"]))

                        if steps:
                            st.write("*Zubereitung:*")
                            for nr, text in steps:
                                st.markdown(f"- *Schritt {nr}:* {text}")
                        else:
                            st.write("_Keine detaillierte Anleitung in der Datenbank gefunden._")

            else:
                st.info("Keine Treffer. Versuch es allgemeiner – z. B. „pasta“ oder „salat“.")

        except Exception as e:
            st.error(f"Fehler bei der Suche: {type(e).__name__}: {e}")
    else:
        st.info("🔎 Gib links einen Suchbegriff ein und wähle die Anzahl der Ergebnisse.")
else:
    st.warning("Bitte zuerst links eine Datenbank verbinden.")

#Shabnams Teil---------------------------------------------------------------------------------------------------#

import os
import sqlite3
import time

import streamlit as st

# unsere KI-Logik
from ai import handle_user_query

# .env laden, falls vorhanden (z.B. für OPENAI_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------
# App-Konfiguration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Smart Cook",
    page_icon="🤖",
    layout="wide",
)

#st.title("🤖 Smart Cook – Dein KI-Rezept-Guide")
st.caption("Frag nach Rezepten oder Zutaten – ich nutze nur die Rezepte aus deiner SQLite-Datenbank 🙂")

# ---------------------------------------------------------
# Session State initialisieren
# ---------------------------------------------------------
if "db_connected" not in st.session_state:
    st.session_state["db_connected"] = False

if "db_path" not in st.session_state:
    st.session_state["db_path"] = "smart_cook_ultra_simple_BIG.db"

if "messages" not in st.session_state:
    # Chat-Historie
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hey 👋 ich bin dein Smart-Cook-Bot. "
                       "Frag mich nach Rezepten oder Ideen – ich arbeite nur mit deiner Datenbank.",
        }
    ]

if "chat_open" not in st.session_state:
    st.session_state["chat_open"] = False

# ---------------------------------------------------------
# Sidebar: Datenbank-Verbindung & Quick Search
# ---------------------------------------------------------
st.sidebar.header("Settings")
st.sidebar.write(
    "This is a simple chat application using SQLite. "
    "Connect to the database and start chatting."
)

db_path_input = st.sidebar.text_input(
    "Database",
    value=st.session_state["db_path"],
    help="Pfad zu deiner SQLite-Datenbank (.db-Datei)",
)

if st.sidebar.button("Connect", key="connect_button"):
    if not db_path_input:
        st.sidebar.error("Bitte gib einen gültigen Datenbankpfad an.")
    elif not os.path.exists(db_path_input):
        st.sidebar.error("Die Datei existiert nicht. Bitte prüfe den Pfad.")
    else:
        st.session_state["db_path"] = db_path_input
        st.session_state["db_connected"] = True
        st.sidebar.success(f"Verbunden mit: {db_path_input}")

st.sidebar.markdown("---")
st.sidebar.subheader("Quick Search")

quick_term = st.sidebar.text_input("Search term (title or ingredient)", placeholder="z.B. pasta, tomato, vegan …")
quick_limit = st.sidebar.slider("Number of results", min_value=5, max_value=50, value=20, step=5)


def quick_search_recipes(db_path: str, term: str, limit: int = 20):
    """Einfache Suche nach Rezepten anhand Titel oder Zutat."""
    if not term:
        return []

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    like = f"%{term.lower()}%"
    sql = """
        SELECT DISTINCT r.id, r.title
        FROM recipes r
        LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
        LEFT JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE lower(r.title) LIKE ? OR lower(i.name) LIKE ?
        ORDER BY r.title
        LIMIT ?
    """
    cur.execute(sql, (like, like, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


if st.session_state["db_connected"] and quick_term:
    try:
        results = quick_search_recipes(st.session_state["db_path"], quick_term, quick_limit)
        st.sidebar.markdown("**Ergebnisse**")
        if not results:
            st.sidebar.info("Keine Treffer gefunden.")
        else:
            for rid, title in results:
                st.sidebar.write(f"- {title} (ID {rid})")
    except Exception as e:
        st.sidebar.error(f"Fehler bei der Quick Search: {e}")
elif quick_term:
    st.sidebar.warning("Bitte zuerst eine Datenbank verbinden.")

# ---------------------------------------------------------
# Hauptbereich: links Erklärung, rechts Chatbot
# ---------------------------------------------------------
#col_left, col_right = st.columns([1, 2])

#with col_left:
#    st.markdown("### ℹ️ Wie du mich nutzen kannst")
 #   st.markdown(
  #      """
   #     - Schreib in normaler Sprache, was du kochen möchtest  
    #      z.B. *"Ich möchte tomato garlic pasta kochen"*  
     #   - Oder frag: *"Gibt es vegane Rezepte?"*  
      #  - Ich suche in deiner Datenbank passende Rezepte  
       #   und erstelle dir eine Schritt-für-Schritt-Anleitung.  
        #- Ich erfinde dabei **keine neuen Rezepte oder Zutaten**.
        #"""
    #)

USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

with st.container():
    with st.expander("💬 Smart Cook – KI Chat öffnen / schließen", expanded=True):

        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {
                    "role": "assistant",
                    "content": "Hey 👋 ich bin dein Smart-Cook-Bot. Frag mich nach Rezepten oder Ideen – ich nutze nur die Rezepte aus der Datenbank.",
                }
            ]

        # --- Bisherige Nachrichten anzeigen ---
        for msg in st.session_state["messages"]:
            avatar = BOT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        # --- Eingabefeld immer unten ---
        user_input = st.chat_input("Was möchtest du heute kochen?")

        # --- Eingabe verarbeiten ---
        if user_input:
            st.session_state["messages"].append({"role": "user", "content": user_input})

            if not st.session_state.get("db_connected", False):
                answer = "Bitte zuerst links eine Datenbank verbinden."
            else:
                try:
                    answer = handle_user_query(st.session_state["db_path"], user_input)
                except Exception as e:
                    answer = f"❌ Fehler: {e}"

            st.session_state["messages"].append({"role": "assistant", "content": answer})

            # Seite refresh → Eingabefeld bleibt unten
            st.rerun()
