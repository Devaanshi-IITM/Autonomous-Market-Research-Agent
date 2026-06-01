# Groq LLM setup

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm(temperature: float = 0.1) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")

    return ChatGroq(
        api_key=api_key,
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=temperature,
        max_tokens=4096,
    )
