from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from typing_extensions import TypeVar

T = TypeVar('T')


@dataclass
class LLMContext:
    llm: ChatOpenAI
