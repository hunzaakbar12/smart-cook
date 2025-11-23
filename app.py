import streamlit as st
import sqlite3
import pandas as pd

# ---- App-Konfiguration ----
st.set_page_config(page_title="Smart Cook", page_icon="🤖", layout="wide")

# ---- Header ----
st.title("🤖 Smart Cook – Dein KI-Rezept-Guide")
st.caption("Frag nach Rezepten oder Zutaten – ich finde passende Ideen in deiner Datenbank 🙂")

# ---- Sidebar: Datenbank ----
st.sidebar.header("Settings")
st.sidebar.write("SQLite Datenbank verbinden")

db_path = st.sidebar.text_input("Database", value="smart_cook_ultra.db")

if st.sidebar.button("Connect"):
    try:
        conn = sqlite3.connect(db_path)
        st.session_state["db_connected"] = True
        st.session_state["db_path"] = db_path
        st.sidebar.success("✅ Verbunden!")
    except Exception as e:
        st.session_state["db_connected"] = False
        st.sidebar.error(f"❌ Verbindung fehlgeschlagen: {e}")

# ---- DB Funktionen ----
def query_db(sql, params=()):
    conn = sqlite3.connect(st.session_state["db_path"])
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)

def get_steps(recipe_id):
    df = query_db("""
        SELECT step_no, instruction
        FROM recipe_steps
        WHERE recipe_id = ?
        ORDER BY step_no
    """, (recipe_id,))
    return df

# ---- Sidebar Suche ----
st.sidebar.divider()
st.sidebar.subheader("Schnelle Suche")
q = st.sidebar.text_input("Suchwörter", placeholder="z.B. pasta, salat, tomate")
top_n = st.sidebar.slider("Anzahl der Ergebnisse", 1, 20)

# ---- Hauptbereich ----
st.subheader("Ergebnisse")

if st.session_state.get("db_connected", False):
    if q.strip():
        try:
            df = query_db("""
                SELECT r.id, r.title, r.servings, d.name AS difficulty
                FROM recipes r
                LEFT JOIN difficulties d ON r.difficulty_id = d.id
                WHERE r.title LIKE ? OR r.id IN (
                    SELECT recipe_id
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE i.name LIKE ?
                )
                LIMIT ?
            """, (f"%{q}%", f"%{q}%", top_n))

            if df.empty:
                st.info("Keine Treffer 😕")
            else:
                for _, row in df.iterrows():
                    with st.expander(f"🍽️ {row['title']}"):
                        st.write(f"**Portionen:** {row['servings']}")
                        st.write(f"**Schwierigkeit:** {row['difficulty']}")

                        ingredients = query_db("""
                            SELECT i.name, ri.amount
                            FROM recipe_ingredients ri
                            JOIN ingredients i ON ri.ingredient_id = i.id
                            WHERE ri.recipe_id = ?
                        """, (row["id"],))
                        
                        if not ingredients.empty:
                            st.write("**Zutaten:**")
                            st.table(ingredients)

                        steps = get_steps(row["id"])
                        if not steps.empty:
                            st.write("**Zubereitung:**")
                            for _, step in steps.iterrows():
                                st.markdown(f"- Schritt {step['step_no']}: {step['instruction']}")
                        else:
                            st.write("_Keine Schritte vorhanden_")

        except Exception as e:
            st.error(f"Fehler: {type(e).__name__}: {e}")
    else:
        st.info("🔎 Suchbegriff eingeben")
else:
    st.warning("Bitte zuerst verbinden ✅")
