# app.py
import streamlit as st
from services import list_tables, run_query, search_recipes

st.set_page_config(
    page_title="Smart Cook",
    page_icon="🍳",
    layout="wide"
)

# ---- Header
st.title("Smart Cook – Datenbrowser")

st.caption("Frag die Datenbank nach Rezepten oder führe eine eigene SQL-Abfrage aus.")

# ---- Sidebar: DB-Status & Navigation
with st.sidebar:
    st.header("Datenbank")
    try:
        tables = list_tables()
        st.success(f"Verbunden • {len(tables)} Tabellen")
        st.write("**Tabellen:**")
        for t in tables:
            st.write(f"• {t}")
    except Exception as e:
        st.error(f"DB-Fehler: {e}")
        tables = []

    st.divider()
    st.subheader("Schnellsuche")
    q = st.text_input("Suchbegriff (Titel/Beschreibung)", placeholder="z.B. pasta, tomaten, vegan …")
    top_n = st.slider("Anzahl Ergebnisse", 5, 50, 20)

# ---- Hauptbereich: Tabs
tab1, tab2 = st.tabs(["🔎 Rezepte suchen", "📝 Eigene SQL"])

with tab1:
    st.subheader("Ergebnisse")
    if q:
        try:
            cols, rows = search_recipes(q, top_n)
            if rows:
                st.dataframe(rows, columns=cols, use_container_width=True, hide_index=True)
            else:
                st.info("Keine Treffer.")
        except Exception as e:
            st.error(f"Fehler bei der Suche: {e}")
    else:
        st.info("Gib links einen Suchbegriff ein.")

with tab2:
    st.subheader("SQL ausführen")
    default_sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    sql = st.text_area("SQL", value=default_sql, height=160, label_visibility="collapsed")
    if st.button("Ausführen", type="primary"):
        try:
            cols, rows = run_query(sql)
            if rows:
                st.dataframe(rows, columns=cols, use_container_width=True, hide_index=True)
            else:
                st.info("Keine Zeilen zurückgegeben.")
        except Exception as e:
            st.error(f"SQL-Fehler: {e}")
