# app.py
import streamlit as st
from services import list_tables, run_query, search_recipes

# ---- Seiteneinstellungen ----
st.set_page_config(
    page_title="Smart Cook",
    page_icon="🤖",
    layout="wide"
)

# ---- Header ----
st.title("🤖 Smart Cook – Dein KI-Rezept-Guide")
st.caption("Frag nach Rezepten oder Zutaten – ich finde passende Ideen in deiner Datenbank.")

# ---- Sidebar: Datenbankstatus & Suche ----
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
    q = st.text_input("Suchbegriff (Titel oder Zutat)", placeholder="z. B. pasta, tomaten, vegan …")
    top_n = st.slider("Anzahl Ergebnisse", 5, 50, 20)

# ---- Hauptbereich mit Tabs ----
tab1, tab2 = st.tabs(["🔎 Rezepte suchen", "📝 Eigene SQL"])

# ---------- TAB 1: Rezeptsuche ----------
with tab1:
    st.subheader("Ergebnisse")

    if q.strip():  # Nur suchen, wenn etwas eingegeben wurde
        try:
            cols, rows = search_recipes(q, top_n)
            if rows:
                st.dataframe(rows, columns=cols, use_container_width=True, hide_index=True)
            else:
                st.info("Keine Treffer. Tipp: versuche allgemeiner zu suchen (z. B. „pasta“).")
        except Exception as e:
            st.error(f"Fehler bei der Suche: {type(e).__name__}: {e}")
    else:
        st.info("🔎 Gib links einen Suchbegriff ein und wähle die Anzahl der Ergebnisse.")

# ---------- TAB 2: Eigene SQL-Abfrage ----------
with tab2:
    st.subheader("SQL ausführen")

    default_sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    sql = st.text_area("SQL", value=default_sql, height=160, label_visibility="collapsed")

    if st.button("SQL ausführen", type="primary"):
        try:
            cols, rows = run_query(sql)
            if rows:
                st.dataframe(rows, columns=cols, use_container_width=True, hide_index=True)
            else:
                st.info("Keine Zeilen zurückgegeben.")
        except Exception as e:

            st.error(f"SQL-Fehler: {e}")

