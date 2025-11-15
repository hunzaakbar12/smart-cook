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
st.sidebar.subheader("Quick Search")
q = st.sidebar.text_input("Search term (title or ingredient)", placeholder="e.g. pasta, tomato, vegan ...")
top_n = st.sidebar.slider("Number of results", 5, 50, 20)

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
