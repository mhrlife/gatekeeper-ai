from typing import Optional

from langchain_core.tools import tool
from langgraph.func import entrypoint, task
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from clients.openai import create_chat_client, MAIN_MODEL


@entrypoint()
async def message_tool_calls(message: str) -> Optional[str]:
    is_bot_mentioned = await detect_bot_mentioned(message)
    if not is_bot_mentioned:
        return None

    return await process_user_request(message)


@task
async def detect_bot_mentioned(message: str) -> bool:
    """
    This function is used to detect if the bot is mentioned in the message
    """
    return "@hey" in message.lower()


class UserRequestResponse(BaseModel):
    """
    The response to the user's request must follow this structure
    """
    request: str = Field(
        description="The user's request asked from the LLM in their message's language"
    )
    response: Optional[str] = Field(
        description=(
            """
The LLM's response to the user's request in their message's language.
If the LLM was not able to respond, this field will be None

# Rules
- don't add any extra information to the response
- don't use markdown or html formatting, pure text with backslash n
                        
            """)
    )
    able_to_respond: bool = Field(
        description="Whether the LLM was able to respond to the user's request or not"
    )


@task
async def process_user_request(message: str) -> UserRequestResponse:
    llm = create_chat_client(MAIN_MODEL)

    llm.bind_tools([
        question_tool,
    ])

    out = await create_react_agent(
        model=llm,
        tools=[question_tool],
        response_format=UserRequestResponse
    ).ainvoke({
        "messages": [
            {"role": "user", "content": message}
        ]
    })

    return out["structured_response"]


@tool
async def question_tool(
        question: str,
) -> str:
    """
    This tool must be used to answer any question or requests the user have, do not use your own memory
    to answer the question, always use this tool
    """
    print("aloooooo")
    llm = create_chat_client(MAIN_MODEL, max_tokens=300).with_structured_output()
    response = await llm.ainvoke(f"""
Your task is to answer user's question in a concise and clear manner. The response language should be the same as the question language.
# Rules
- don't ask for follow up, generate a response to the question
- don't add any extra information to the response
- don't say "I am not sure", generate a response to the question

question: {question}
""")
    return response
