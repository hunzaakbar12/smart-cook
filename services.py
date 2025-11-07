# services.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# 1) .env laden und Client bauen
load_dotenv()  # liest OPENAI_API_KEY aus .env im Projektroot
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2) Einfache Helferfunktion für KI-Antworten
def ask_openai(prompt: str) -> str:
    """
    Schickt einen Prompt an OpenAI und gibt den Antworttext zurück.
    """
    resp = client.chat.completions.create(
        model="gpt-4o-mini",        # schnell & günstig
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
    )
    return resp.choices[0].message.content.strip() 