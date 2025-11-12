import streamlit as st
from services import ask_openai

st.title("Smart Cook – OpenAI Test")

prompt = st.text_input("Frage an die KI:", "Gib mir eine schnelle vegetarische Pasta-Idee in 1 Satz.")
if st.button("Fragen"):
    with st.spinner("Denke..."):
        try:
            answer = ask_openai(prompt)
            st.write(answer)
        except Exception as e:
            st.error(f"Fehler bei der KI-Anfrage: {e}")git clone https://github.com/hunzaakbar12/smart-cook.git
cd smart-cook
