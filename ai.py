import sqlite3
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# .env laden (API-Key usw.)
load_dotenv()

# LLM vorbereiten
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.4)

# Systemprompt: erklärt der KI, wie sie sich verhalten soll
AI_STYLE_PROMPT = """
Du bist SmartCook, ein freundlicher Kochassistent.
•⁠  ⁠Nutze primär die Informationen aus der Rezeptliste.
•⁠  ⁠Wenn etwas nicht in den Daten steht, darfst du basierend auf allgemeinem Kochwissen Tipps geben.
•⁠  ⁠Erfinde KEINE komplett neuen Rezepte.
•⁠  ⁠Wenn der Nutzer Bedingungen nennt (z.B. "nur vegan", "max. 10 Minuten"),
  passe die Antwort daran an.
•⁠  ⁠Sei locker, freundlich und praktisch.
"""

# Holt alle Rezepte aus der Datenbank und baut einen großen Textblock
def load_recipes_text(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    lines = []

    # Alle Rezepte
    cur.execute("""
        SELECT r.id, r.title, r.servings, r.description,
               r.prep_minutes, r.cook_minutes, r.is_vegan,
               d.name AS difficulty_name, d.level AS difficulty_level
        FROM recipes r
        LEFT JOIN difficulties d ON d.id = r.difficulty_id
        ORDER BY r.id
    """)
    recipes = cur.fetchall()

    for (
        recipe_id,
        title,
        servings,
        description,
        prep_minutes,
        cook_minutes,
        is_vegan,
        difficulty_name,
        difficulty_level,
    ) in recipes:
        lines.append("----------------------------------------------------")
        lines.append(f"Rezept-ID: {recipe_id}")
        lines.append(f"Titel: {title}")

        if servings:
            lines.append(f"Portionen: {servings}")
        if description:
            lines.append(f"Beschreibung: {description}")

        prep = prep_minutes or 0
        cook = cook_minutes or 0
        total = prep + cook
        if total > 0:
            lines.append(f"Zeit: Vorbereitung {prep} Min, Kochen {cook} Min (gesamt {total} Min)")

        if is_vegan is not None:
            lines.append(f"Vegan: {'ja' if is_vegan else 'nein'}")

        if difficulty_name:
            diff = f"Schwierigkeitsgrad: {difficulty_name}"
            if difficulty_level:
                diff += f" (Level {difficulty_level})"
            lines.append(diff)

        # Zutaten
        cur.execute("""
            SELECT i.name, ri.amount
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.recipe_id = ?
            ORDER BY i.name
        """, (recipe_id,))
        ingredients = cur.fetchall()
        if ingredients:
            lines.append("Zutaten:")
            for name, amount in ingredients:
                text = f"{amount or ''} {name}".strip()
                lines.append(f"- {text}")

        # Schritte
        cur.execute("""
            SELECT step_no, instruction
            FROM recipe_steps
            WHERE recipe_id = ?
            ORDER BY step_no
        """, (recipe_id,))
        steps = cur.fetchall()
        if steps:
            lines.append("Schritte:")
            for step_no, instruction in steps:
                lines.append(f"{step_no}. {instruction}")

        lines.append("")

    conn.close()
    return "\n".join(lines)

# Prompt-Template für die Konversation
main_prompt = ChatPromptTemplate.from_template(
    AI_STYLE_PROMPT
    + """
Hier ist die komplette Liste aller gespeicherten Rezepte:

================= REZEPTLISTE START =================
{recipes_block}
================= REZEPTLISTE ENDE ==================

Benutzerfrage:
\"\"\"{user_query}\"\"\"

Antworte:
•⁠  ⁠basierend auf den Rezeptdaten
•⁠  ⁠mit verständlichen, sinnvollen Kochtipps
"""
)

main_chain = main_prompt | llm | StrOutputParser()

# Diese Funktion rufst du von außen auf
def handle_user_query(db_path: str, query: str) -> str:
    query = query.strip()
    if not query:
        return "Bitte gib eine Frage oder einen Wunsch ein 🙂."

    recipes_block = load_recipes_text(db_path)
    if not recipes_block.strip():
        return "In der Datenbank sind keine Rezepte gespeichert."

    answer = main_chain.invoke({
        "user_query": query,
        "recipes_block": recipes_block
    })
    return answer.strip()