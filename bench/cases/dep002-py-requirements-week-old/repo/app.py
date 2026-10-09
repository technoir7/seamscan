import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

st.title("Docs assistant")
question = st.text_input("Ask a question about the docs")
if question:
    reply = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}],
    )
    st.write(reply.choices[0].message.content)
