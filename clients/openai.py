import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

MAIN_MODEL = "google/gemini-2.0-flash-001"


def create_chat_client(model_name: str) -> ChatOpenAI:
    load_dotenv()

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_KEY"),
        model_name=model_name
    )
