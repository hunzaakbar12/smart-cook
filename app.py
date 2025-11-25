import streamlit as st
import sqlite3
import pandas as pd
import time


from ai import handle_user_query


# ------------------------------------------------------
# App Setup
# ------------------------------------------------------
st.set_page_config(page_title="Smart Cook", page_icon="🤖", layout="wide")

st.title("🤖 Smart Cook – Dein KI-Rezept-Guide")
st.caption("Frag nach Rezepten oder chatte mit dem Kochbot! 🙂")


# ------------------------------------------------------
# Session Init
# ------------------------------------------------------
if "db_connected" not in st.session_state:
    st.session_state["db_connected"] = False

if "db_path" not in st.session_state:
    st.session_state["db_path"] = None

if "messages" not in st.session_state:
    st.session_state["messages"] = []


# ------------------------------------------------------
# Sidebar: DB Connect
# ------------------------------------------------------
st.sidebar.header("Settings")
db_path = st.sidebar.text_input("Database", value="smart_cook_ultra.db")

if st.sidebar.button("Connect"):
    try:
        conn = sqlite3.connect(db_path)
        conn.close()

        st.session_state["db_connected"] = True
        st.session_state["db_path"] = db_path

        st.sidebar.success("✅ Verbunden!")
        st.balloons()   # 🎈 Ballons


    except Exception as e:
        st.session_state["db_connected"] = False
        st.sidebar.error(f"❌ Verbindung fehlgeschlagen: {e}")


# ------------------------------------------------------
# DB Helpers
# ------------------------------------------------------
def query_db(sql, params=()):
    conn = sqlite3.connect(st.session_state["db_path"])
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


# ------------------------------------------------------
# Rezepte Suche
# ------------------------------------------------------
st.subheader("🔎 Rezepte")

if st.session_state["db_connected"]:
    q = st.sidebar.text_input("Suchwörter", placeholder="z.B. pasta, salat, tomate")
    top_n = st.sidebar.slider("Anzahl der Ergebnisse", 1, 20)

    if q.strip():
        try:
            df = query_db("""
                SELECT r.id, r.title, r.servings
                FROM recipes r
                LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
                LEFT JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE r.title LIKE ? OR i.name LIKE ?
                GROUP BY r.id
                LIMIT ?
            """, (f"%{q}%", f"%{q}%", top_n))

            if df.empty:
                st.info("Keine Treffer 😕")

            else:
                for _, row in df.iterrows():
                    with st.expander(f"🍽️ {row['title']}"):
                        st.write(f"**Portionen:** {row['servings']}")

                        ingredients = query_db("""
                            SELECT i.name, ri.amount
                            FROM recipe_ingredients ri
                            JOIN ingredients i ON ri.ingredient_id = i.id
                            WHERE ri.recipe_id = ?
                        """, (row["id"],))
                        st.write("**Zutaten:**")
                        st.table(ingredients)

                        steps = query_db("""
                            SELECT step_no, instruction
                            FROM recipe_steps
                            WHERE recipe_id = ?
                        """, (row["id"],))
                        st.write("**Zubereitung:**")

                        for _, step in steps.iterrows():
                            st.markdown(f"- Schritt {step['step_no']}: {step['instruction']}")

        except Exception as e:
            st.error(f"Fehler: {e}")

else:
    st.warning("Bitte zuerst verbinden ✅")


# ------------------------------------------------------
# Chat
# ------------------------------------------------------
st.divider()
st.subheader("💬 Chat mit dem KI-Koch")


for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ------------------------------------------------------
# Eingabe + Tipp Animation
# ------------------------------------------------------
user_input = st.chat_input("Was möchtest du heute kochen?")

if user_input:

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state["messages"].append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        typing = st.empty()

        for dots in ["🤖 schreibt", "🤖 schreibt.", "🤖 schreibt..", "🤖 schreibt..."]:
            typing.markdown(dots)
            time.sleep(0.3)

        if not st.session_state["db_connected"]:
            answer = "Bitte verbinde zuerst eine Datenbank ✅"
        else:
            try:
                answer = handle_user_query(st.session_state["db_path"], user_input)
            except Exception as e:
                answer = f"❌ Fehler: {e}"

        typing.empty()
        st.markdown(answer)

    st.session_state["messages"].append({"role": "assistant", "content": answer})
