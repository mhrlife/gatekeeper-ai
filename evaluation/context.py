from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from typing_extensions import TypeVar, Generic

T = TypeVar('T')


@dataclass
class LLMContext:
    llm: ChatOpenAI
