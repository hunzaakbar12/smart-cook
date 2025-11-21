import sqlite3
from typing import List, Tuple, Optional

# LangChain-Imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# .env laden (OPENAI_API_KEY usw.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------
# Globaler System-/Stil-Prompt – "Gehirn" der KI
# ---------------------------------------------------------
AI_STYLE_PROMPT = """
Du bist „Smart Cook“, ein freundlicher, klarer und leicht humorvoller Kochassistent.

DEINE QUELLE:
- Du arbeitest AUSSCHLIESSLICH mit den Informationen, die dir im Prompt übergeben werden.
- Diese Informationen kommen aus einer SQLite-Datenbank (Rezepte, Zutaten, Schritte, Zeiten).
- Alles, was NICHT im Datenblock steht, gilt für dich als unbekannt.

HARTE REGELN:
- Du erfindest KEINE neuen Rezepte, Zutaten, Zeiten, Mengen oder Schritte.
- Wenn eine Information nicht im Datenblock steht, sagst du das ehrlich.
  Beispiel: „In den gespeicherten Daten steht dazu leider nichts.“
- Du darfst Formulierungen nur sprachlich glätten und strukturieren,
  aber den INHALT nicht verändern.
- Wenn du etwas schätzt oder interpretierst, musst du klar sagen, dass es eine Schätzung ist.

AUFGABENMODI:
- Wenn die Person kochen möchte („ich will … kochen“, „gib mir das Rezept für …“):
  -> Gib eine freundliche, gut strukturierte Anleitung auf Basis der vorhandenen Zutaten
     und/oder Schritte aus der Datenbank.
- Wenn nach Zeit, Dauer, Portionen oder anderen Fakten gefragt wird:
  -> Beantworte die Frage nur mit den vorhandenen Werten (z.B. Minuten aus den Schritt-Daten).
  -> Bei Zeitfragen soll die Antwort kurz und fokussiert sein, keine ganze Rezeptanleitung.
- Wenn nach Zutaten gefragt wird:
  -> Liste die Zutaten übersichtlich auf.
- Wenn es kein passendes Rezept gibt:
  -> Sag das klar und biete nur Rezepte an, die im Datenblock vorhanden sind.

STIL:
- Schreibe auf natürlichem, lockerem Deutsch (duzen ist ok).
- Sei freundlich, aber nicht übertrieben.
- Struktur (Überschriften, Listen) ist willkommen, wenn es hilft.
- Emojis sparsam einsetzen (z.B. 🙂, 🍝, 🍽️, ⏲️).
"""

# ---------------------------------------------------------
# LLM-Instanzen
# ---------------------------------------------------------
llm_mini = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3,
)

llm_steps = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.5,
)

# ---------------------------------------------------------
# DB-Helper
# ---------------------------------------------------------


def search_recipe_by_name(db_path: str, term: str) -> List[Tuple[int, str, int]]:
    """Suche Rezepte nach Titel (Spalte: recipes.title)."""
    if not term:
        return []
    like = f"%{term.lower()}%"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql = """
        SELECT id, title, servings
        FROM recipes
        WHERE lower(title) LIKE ?
        ORDER BY title
    """
    cur.execute(sql, (like,))
    rows = cur.fetchall()
    conn.close()
    return rows


def load_recipe_full(db_path: str, recipe_id: int):
    """
    Lade alle relevanten Infos zu einem Rezept:
    - Titel, Portionen
    - Zutatenliste
    - Schritte inkl. Minuten (falls vorhanden)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Rezept-Stammdaten
    cur.execute(
        "SELECT title, servings FROM recipes WHERE id = ?",
        (recipe_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    title, servings = row

    # Zutaten
    cur.execute(
        """
        SELECT i.name
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY i.name
        """,
        (recipe_id,),
    )
    ingredients = [r[0] for r in cur.fetchall()]

    # Schritte (optional mit Minuten)
    cur.execute(
        """
        SELECT step_no, instruction, minutes
        FROM recipe_steps
        WHERE recipe_id = ?
        ORDER BY step_no
        """,
        (recipe_id,),
    )
    steps = cur.fetchall()

    conn.close()

    return {
        "id": recipe_id,
        "title": title,
        "servings": servings,
        "ingredients": ingredients,
        "steps": steps,  # Liste von (step_no, instruction, minutes)
    }


def load_all_recipes_for_ai(db_path: str):
    """Lade alle Rezepte inkl. zusammengefasster Zutaten für Vorschläge."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql = """
        SELECT r.id, r.title, r.servings,
               GROUP_CONCAT(i.name, ', ')
        FROM recipes r
        JOIN recipe_ingredients ri ON ri.recipe_id = r.id
        JOIN ingredients i ON i.id = ri.ingredient_id
        GROUP BY r.id, r.title, r.servings
        ORDER BY r.id
    """
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_quick_recipes(db_path: str, limit: int = 5):
    """
    Liefert Rezepte mit der geringsten Gesamt-Minutenzeit
    (Summe der 'minutes' aus recipe_steps).
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql = """
        SELECT r.id,
               r.title,
               r.servings,
               COALESCE(SUM(rs.minutes), 0) AS total_minutes
        FROM recipes r
        LEFT JOIN recipe_steps rs ON rs.recipe_id = r.id
        GROUP BY r.id, r.title, r.servings
        HAVING total_minutes > 0
        ORDER BY total_minutes ASC
        LIMIT ?
    """
    cur.execute(sql, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows  # [(id, title, servings, total_minutes), ...]


# ---------------------------------------------------------
# 1) User-Text -> Suchbegriff
# ---------------------------------------------------------


search_term_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Der Benutzer / die Benutzerin schreibt, was er/sie kochen oder wissen möchte.

Text:
\"\"\"{user_text}\"\"\"


Extrahiere einen einzigen kurzen Suchbegriff, mit dem man in einer
Rezept-Datenbank nach passenden TITELN suchen würde.

Beispiele:
- "Ich möchte Pasta kochen" -> Pasta
- "Hast du ein Rezept für Linsen-Bolognese?" -> Linsen-Bolognese
- "Ich suche etwas mit Reis und Gemüse" -> Reis

Gib NUR den Suchbegriff zurück, ohne Erklärung, ohne Anführungszeichen.
Wenn du dir unsicher bist, gib einfach den Originaltext zurück.
"""
)

search_term_chain = search_term_prompt | llm_mini | StrOutputParser()


def extract_search_term(user_text: str) -> str:
    user_text = user_text.strip()
    if not user_text:
        return ""
    try:
        result = search_term_chain.invoke({"user_text": user_text})
        return result.strip() or user_text
    except Exception:
        return user_text


def is_low_effort_question(text: str) -> bool:
    """
    Erkenne Fragen wie:
    - welche Rezepte haben wenig Aufwand?
    - was geht schnell?
    - hast du schnelle Rezepte?
    """
    t = text.lower()
    keywords = [
        "wenig aufwand",
        "schnell",
        "schnelle rezepte",
        "geht schnell",
        "einfach und schnell",
        "nicht viel arbeit",
    ]
    return any(kw in t for kw in keywords)


# ---------------------------------------------------------
# 2) Kontextblock für ein Rezept aus der DB bauen
# ---------------------------------------------------------


def build_recipe_context(recipe: dict) -> str:
    """
    Erzeugt einen klaren Textblock mit allen Infos aus der DB,
    den wir dem LLM als Kontext geben.
    """
    lines: List[str] = []
    lines.append(f"Rezept: {recipe['title']}")
    lines.append(f"Portionen: {recipe['servings']}")
    lines.append("")
    lines.append("Zutaten:")
    for name in recipe["ingredients"]:
        lines.append(f"- {name}")
    lines.append("")

    if recipe["steps"]:
        lines.append("Schritte aus der Datenbank:")
        for step_no, instr, minutes in recipe["steps"]:
            minutes_part = f" (ca. {int(minutes)} Minuten)" if minutes is not None else ""
            lines.append(f"{step_no}. {instr}{minutes_part}")
    else:
        lines.append("Es sind KEINE Kochschritte in der Datenbank gespeichert.")
    return "\n".join(lines)


# ---------------------------------------------------------
# 3) QA-Chain: beliebige Frage + DB-Kontext
# ---------------------------------------------------------


qa_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Hier sind alle Informationen aus der Datenbank zu einem Rezept:

---------------- DB-DATEN-START ----------------
{db_context}
---------------- DB-DATEN-ENDE ------------------

Frage der Benutzerin / des Benutzers:
\"\"\"{user_query}\"\"\"

WICHTIG:
- Nutze ausschließlich die Informationen aus dem DB-Datenblock.
- Wenn die Frage etwas verlangt, das dort nicht drinsteht, sag klar,
  dass diese Information nicht gespeichert ist.
- Wenn die Frage hauptsächlich nach der DAUER oder ZEIT fragt
  (z.B. "wie lange dauert ...", "wie viele Minuten ..."):
  -> antworte kurz und fokussiert mit einer sinnvollen Zeitangabe,
     die sich aus den vorhandenen Minutenangaben oder Formulierungen in den Schritten ableiten lässt.
  -> gib in diesem Fall KEINE komplette Schritt-für-Schritt-Anleitung aus.
- Wenn die Frage nach einer Anleitung oder dem Rezept fragt
  (z.B. "wie mache ich ...", "gib mir das Rezept für ..."):
  -> gib eine gut strukturierte Antwort mit Einleitung, Schritten und ggf. Tipp,
     aber erfinde keine neuen Zutaten, Zeiten oder Zwischenschritte.

Antworte auf Deutsch im oben beschriebenen Stil.
"""
)

qa_chain = qa_prompt | llm_steps | StrOutputParser()

# ---------------------------------------------------------
# 4) Vorschlags-Chain, wenn kein direktes Rezept gefunden wurde
# ---------------------------------------------------------


suggest_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Der Benutzer / die Benutzerin stellt folgende Frage:
\"\"\"{user_query}\"\"\"


Du hast Zugriff auf diese Rezepte aus der Datenbank:
{recipes_block}

WICHTIG:
- Du darfst nur Rezepte aus dieser Liste verwenden.
- Du darfst keine neuen Rezepte erfinden.

Wenn der Benutzer nach einem bestimmten Gericht fragt (z.B. "Pizza"),
das NICHT als Titel in der Liste vorkommt:
1. Sag klar, dass dieses Rezept in der Datenbank nicht vorhanden ist.
2. Biete 3–6 Rezepte aus der Liste an, die thematisch passen
   (ähnliche Zutaten, ähnliche Art Gericht).

Wenn die Frage allgemeiner ist (z.B. "gibt es vegane rezepte?"):
1. Sag kurz, ob passende Rezepte in der Liste vorhanden sind.
2. Wähle 3–6 sinnvolle Rezepte aus und erläutere in 1 Satz, warum sie passen.

Antwortstil:
- Erst eine ehrliche, kurze Reaktion.
- Dann die Liste der passenden Rezepte mit Erklärung.
- Optional eine Empfehlung, womit die Person starten könnte.
"""
)

suggest_chain = suggest_prompt | llm_mini | StrOutputParser()


def suggest_recipes_from_query(
    db_path: str,
    user_query: str,
    search_term: Optional[str] = None,
) -> str:
    recipes = load_all_recipes_for_ai(db_path)
    if not recipes:
        return "In der Datenbank sind aktuell keine Rezepte gespeichert."

    recipe_lines = []
    for rid, title, servings, ingredients in recipes:
        recipe_lines.append(
            f"- ID {rid}: {title} (für {servings} Portionen) – Zutaten: {ingredients}"
        )
    recipes_block = "\n".join(recipe_lines)

    try:
        result = suggest_chain.invoke(
            {
                "user_query": user_query,
                "recipes_block": recipes_block,
            }
        )
        return result.strip()
    except Exception as e:
        return (
            "Beim Erzeugen der Vorschläge ist ein Fehler aufgetreten: "
            f"{type(e).__name__}: {e}"
        )


# ---------------------------------------------------------
# 5) Antwort für „wenig Aufwand / schnelle Rezepte“
# ---------------------------------------------------------


def answer_quick_recipes(db_path: str) -> str:
    rows = get_quick_recipes(db_path, limit=5)
    if not rows:
        return (
            "In der Datenbank sind leider keine Rezepte mit hinterlegter Zeit gespeichert. "
            "Deshalb kann ich nicht sagen, welche besonders wenig Aufwand haben."
        )

    lines: List[str] = []
    lines.append("Hier sind ein paar Rezepte mit wenig Zeitaufwand:\n")
    for idx, (rid, title, servings, total_minutes) in enumerate(rows, start=1):
        lines.append(
            f"{idx}. {title} (ID {rid}) – ca. {int(total_minutes)} Minuten, für {servings} Portionen"
        )
    lines.append(
        "\nDie Liste ist nach Zeit sortiert – oben stehen die Gerichte mit der kürzesten Zubereitungsdauer."
    )
    return "\n".join(lines)


# ---------------------------------------------------------
# 6) Hauptfunktion für Streamlit
# ---------------------------------------------------------


def handle_user_query(db_path: str, query: str) -> str:
    """
    Zentrale Funktion für die App:
    - nimmt den vollständigen User-Text,
    - sucht passende Rezepte,
    - liefert entweder:
      * eine intelligente, aber streng DB-gebundene Antwort zu einem Rezept
      * eine Liste von Vorschlägen
      * oder einen Hinweis, dass nichts vorhanden ist.
    """
    query = query.strip()
    if not query:
        return "Bitte gib eine Frage oder einen Rezeptnamen ein 🙂."

    # Spezieller Fall: „wenig Aufwand / schnell“
    if is_low_effort_question(query):
        return answer_quick_recipes(db_path)

    # 1) Suchbegriff extrahieren
    search_term = extract_search_term(query)

    # 2) Rezepte per Titel suchen
    matches = search_recipe_by_name(db_path, search_term)

    # 3) Kein Treffer -> Vorschlags-Chain
    if not matches:
        return suggest_recipes_from_query(db_path, query, search_term)

    # 4) Mehrere Treffer -> Auswahl anzeigen
    if len(matches) > 1:
        titles = "\n".join(f"- {title} (ID {rid})" for rid, title, _ in matches)
        return (
            "Ich habe mehrere passende Rezepte in der Datenbank gefunden:\n"
            f"{titles}\n\n"
            "Sag mir bitte den genauen Namen oder die ID des Rezepts, "
            "damit ich dir gezielt weiterhelfen kann. 🍽️"
        )

    # 5) Genau ein Rezept: vollständigen DB-Kontext aufbauen
    recipe_id, title, servings = matches[0]
    recipe_data = load_recipe_full(db_path, recipe_id)

    if not recipe_data:
        return (
            f"Ich habe ein Rezept mit der ID {recipe_id} gefunden, "
            "konnte aber die Details nicht laden."
        )

    db_context = build_recipe_context(recipe_data)

    # 6) LLM-Antwort auf Basis der DB-Daten und der ursprünglichen User-Frage
    try:
        answer = qa_chain.invoke(
            {
                "db_context": db_context,
                "user_query": query,
            }
        )
        return answer.strip()
    except Exception as e:
        return (
            "Beim Erzeugen der Antwort ist ein Fehler aufgetreten: "
            f"{type(e).__name__}: {e}"
        )
