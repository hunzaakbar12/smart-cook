import os
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
# Globaler Stil-Prompt – so "denkt" deine KI
# ---------------------------------------------------------
AI_STYLE_PROMPT = """
Du bist ein freundlicher, klarer und hilfsbereiter Kochassistent – ähnlich wie ChatGPT.
Du:
- antwortest zuerst direkt auf die Frage der Person,
- bleibst ehrlich, wenn etwas NICHT vorhanden ist,
- bietest danach passende Alternativen aus der Datenbank an,
- schreibst auf natürlichem, lockeren Deutsch (duzen ist ok),
- benutzt Emojis sparsam und passend (z.B. 🙂, 🍝, 🍽️).

Wichtige Regeln:
- Du darfst KEINE neuen Rezepte oder Zutaten erfinden.
- Du arbeitest ausschließlich mit den Rezepten und Zutaten,
  die dir im Prompt gegeben werden (das sind die Daten aus der Datenbank).
- Wenn ein gewünschtes Rezept nicht vorhanden ist, sagst du das klar:
  z.B. „Dieses Rezept gibt es in der Datenbank leider nicht.“
  und bietest dann sinnvolle Alternativen an.
"""

# ---------------------------------------------------------
# LLMs (LangChain)
# ---------------------------------------------------------
llm_mini = ChatOpenAI(
    model="gpt-4.1-mini",  # oder das Campus-Modell
    temperature=0.3,
)

llm_steps = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.7,
)

# ---------------------------------------------------------
# 1) DB-Helper – passen zu deiner Datenbank!
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


def load_ingredients(db_path: str, recipe_id: int):
    """Lade Zutaten zu einem Rezept (joins recipe_ingredients + ingredients)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    sql = """
        SELECT i.name, ri.qty, ri.unit, ri.note
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY ri.ingredient_id
    """
    cur.execute(sql, (recipe_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


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

# ---------------------------------------------------------
# 2) LangChain-Chain: User-Satz -> Suchbegriff
# ---------------------------------------------------------

search_term_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Der Benutzer / die Benutzerin schreibt, was er/sie kochen möchte.

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

# ---------------------------------------------------------
# 3) LangChain-Chain: Schritt-für-Schritt-Anleitung
# ---------------------------------------------------------

def ingredients_to_block(ingredients) -> str:
    lines = []
    for name, qty, unit, note in ingredients:
        qty_part = f"{qty}" if qty is not None else ""
        unit_part = f" {unit}" if unit else ""
        note_part = f" ({note})" if note else ""
        line = f"- {qty_part}{unit_part} {name}{note_part}".strip()
        lines.append(line)
    return "\n".join(lines)


steps_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Erstelle eine ausführliche, gut strukturierte Schritt-für-Schritt-Anleitung
für das folgende Rezept. Du MUSST dich strikt an die Zutatenliste halten
und darfst keine neuen Zutaten oder Mengen erfinden.

Rezeptname: {title}
Portionen: {servings}

Zutaten:
{ingredients_block}

Schreibe die Antwort auf Deutsch in etwa diesem Format:

## Kurze Einleitung
1–3 Sätze, was das für ein Gericht ist und worauf man achten sollte.

## Schritte
1. ...
2. ...
3. ...

## Tipp
Ein kurzer Tipp zum Variieren oder Anrichten des Gerichts.
"""
)

steps_chain = steps_prompt | llm_steps | StrOutputParser()


def generate_steps_from_db(title: str, servings: int, ingredients) -> str:
    ing_block = ingredients_to_block(ingredients)
    try:
        result = steps_chain.invoke(
            {
                "title": title,
                "servings": servings,
                "ingredients_block": ing_block,
            }
        )
        return result.strip()
    except Exception as e:
        return (
            "Beim Erzeugen der Anleitung ist ein Fehler aufgetreten: "
            f"{type(e).__name__}: {e}"
        )

# ---------------------------------------------------------
# 4) LangChain-Chain: Allgemeine Fragen -> Vorschläge
# ---------------------------------------------------------

suggest_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Der Benutzer / die Benutzerin stellt folgende Frage:
\"\"\"{user_query}\"\"\"


Du hast Zugriff auf diese Rezepte aus der Datenbank:
{recipes_block}

Wenn der Benutzer nach einem bestimmten Gericht fragt (z.B. "Pizza"),
das NICHT als Titel in der Liste vorkommt, dann:
1. Sag zuerst klar und höflich, dass es dieses Rezept nicht in der Datenbank gibt.
2. Biete danach 3–6 passende Alternativen aus der Datenbank an und erkläre kurz,
   warum sie zur Anfrage passen (z.B. ähnliche Zutaten, ähnliche Art Gericht).

Wenn die Frage allgemeiner ist (z.B. "gibt es vegane rezepte?"),
dann:
1. Sag kurz, ob und welche Rezepte gut zur Anfrage passen.
2. Wähle 3–6 sinnvolle Rezepte aus und erläutere in 1 Satz, warum.

Du darfst keine neuen Rezepte oder Zutaten erfinden.
Antworte auf Deutsch in etwa diesem Stil:

[Erste, ehrliche Reaktion]
[Liste der Alternativen mit kurzer Erklärung]
[Optional: eine Empfehlung, womit die Person starten könnte]
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
# 5) Hauptfunktion für Streamlit
# ---------------------------------------------------------

def handle_user_query(db_path: str, query: str) -> str:
    """
    Nimmt den vollen User-Satz und liefert:
    - Liste von Treffern
    - Anleitung zu einem Rezept
    - oder Vorschläge, wenn es kein direktes Rezept gibt.
    """
    query = query.strip()
    if not query:
        return "Bitte gib eine Frage oder einen Rezeptnamen ein 🙂."

    search_term = extract_search_term(query)

    matches = search_recipe_by_name(db_path, search_term)

    if not matches:
        return suggest_recipes_from_query(db_path, query, search_term)

    if len(matches) > 1:
        titles = "\n".join(f"- {title} (ID {rid})" for rid, title, _ in matches)
        return (
            "Ich habe mehrere passende Rezepte in der Datenbank gefunden:\n"
            f"{titles}\n\n"
            "Sag mir bitte den genauen Namen oder die ID des Rezepts, "
            "damit ich dir eine ausführliche Schritt-für-Schritt-Anleitung geben kann. 🍽️"
        )

    recipe_id, title, servings = matches[0]
    ingredients = load_ingredients(db_path, recipe_id)

    if not ingredients:
        return (
            f"Ich habe das Rezept **{title}** gefunden, "
            "aber in der Datenbank sind keine Zutaten dazu hinterlegt."
        )

    steps_text = generate_steps_from_db(title, servings, ingredients)
    return f"🍝 **{title}** (für {servings} Portionen)\n\n{steps_text}"
