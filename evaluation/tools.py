from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from structlog import get_logger

from clients.openai import create_chat_client, MAIN_MODEL

logger = get_logger()

# --- LLM-based Bot Mention and Request Check ---

BOT_MENTION_CHECK_PROMPT = """
You are an AI assistant that determines if a user's message is a direct request or question to a bot.
The bot is known by names like "Warden", "bot", "ربات", "gatekeeper", "ربات جون".

Analyze the following user message:
"{USER_MESSAGE}"

Is this message a direct question, command, or request to the bot?
Consider:
- Explicit questions to the bot (e.g., "Warden, what is X?", "Bot, can you help me?").
- Commands to the bot (e.g., "ربات, tell me about Y.").
- Implicit requests where the bot is addressed (e.g., "I need help with Golang, bot.").

Do NOT consider:
- General statements or discussions that happen to contain one of the bot's names but are not addressing the bot with a specific request.
- Messages where the bot's name is used metaphorically or in a non-addressing way.
- Questions directed at other users, even if the bot's name is mentioned in passing.

Your primary goal is to identify if the user intends to engage the bot for an answer or action.
"""


class BotMentionCheckResult(BaseModel):
    is_direct_request_to_bot: bool = Field(
        description="True if the user message is a direct request, question, or command to the bot. False otherwise."
    )
    user_request: str = Field(
        description=(
            "The user's request or question to the bot, if identified. \n"
            "This should be a summarized, concise version of the user's message, in the bot's own words.\n"
            "This must be kept as the same language as the user's input\n"
            "# Example:\n"
            "# User message: 'Warden, can you tell me about Golang?'\n"
            "# Bot request: 'Can you tell me about Golang?'\n"
            "# User message: 'I need help with Golang, bot.'\n"
            "# Bot request: 'Can you help me with Golang?'\n"
        )
    )


async def is_user_making_direct_request_to_bot(user_message: str) -> BotMentionCheckResult:
    """
    Uses an LLM to determine if the user's message is a direct request or question to the bot.
    """
    llm = create_chat_client(MAIN_MODEL)
    prompt_for_mention_check = BOT_MENTION_CHECK_PROMPT.format(USER_MESSAGE=user_message)

    try:
        response = await llm.with_structured_output(BotMentionCheckResult).ainvoke(prompt_for_mention_check)
        logger.info("Bot mention check LLM call successful",
                    user_message=user_message,
                    is_request=response.is_direct_request_to_bot,
                    request=response.user_request)
        return response
    except Exception as e:
        logger.error("Error in LLM-based bot mention check",
                     user_message=user_message, error=e, exc_info=True)
        # Fallback: if the check fails, assume it's not a direct request to be safe
        # and avoid unnecessary ReAct agent calls.
        return False


# --- Prompts for Tools ---

GOLANG_QUESTION_PROMPT = """
You are an expert in Golang, answer to user's question regarding golang.
# Rules
- Your response is clean, prettry, and well formatted, without Markdown or HTML formatting, only use backslash n.
- Your message must be concise and to the point.
- You must not include any disclaimers or unnecessary information.
Users Question: {QUESTION}
"""


# --- Tool Implementations ---

async def golang_question_tool(question: str) -> str:
    """
    Answers a question about Golang using an LLM.
    Input is the question string.
    """
    logger.info("Executing golang_question_tool", question=question)
    if not question:
        return "No question provided for the Golang tool."

    llm = create_chat_client(
        MAIN_MODEL,
        max_tokens=300
    )
    prompt_for_golang_llm = GOLANG_QUESTION_PROMPT.format(QUESTION=question)

    try:
        response = await llm.ainvoke(prompt_for_golang_llm)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error("Error in golang_question_tool LLM call", question=question, error=e, exc_info=True)
        return "Sorry, I encountered an error while trying to answer the Golang question."


_tool_agent_instance = None


def get_react_agent():
    """
    Initializes and returns the ReAct agent.
    Caches the agent instance globally.
    """
    global _tool_agent_instance
    if _tool_agent_instance is None:
        llm = create_chat_client(MAIN_MODEL)
        tools = [golang_question_tool]

        _tool_agent_instance = create_react_agent(
            model=llm,
            tools=tools,
        )
        logger.info("ReAct agent initialized with custom system message and response_format.")

    return _tool_agent_instance


async def invoke_react_agent_for_tool_use(user_message: str) -> Optional[str]:
    """
    Invokes the ReAct agent with the user's message if an LLM pre-check determines
    the user is making a direct request to the bot.
    If the ReAct agent then confirms Warden was mentioned and a reply is generated,
    it returns the agent's reply_text. Otherwise, it returns None.
    """
    logger.info("Attempting to invoke ReAct agent", user_message=user_message)

    is_direct_request = await is_user_making_direct_request_to_bot(user_message)

    if not is_direct_request.is_direct_request_to_bot:
        logger.info(
            "LLM pre-check determined user message is not a direct request to the bot. Skipping ReAct agent invocation.",
            user_message=user_message)

        return None

    logger.info("LLM pre-check confirmed a direct request to the bot. Proceeding with ReAct agent invocation.",
                user_message=is_direct_request.user_request)
    agent = get_react_agent()

    input_payload = {"messages": [HumanMessage(content=is_direct_request.user_request)]}
    out = await agent.ainvoke(input_payload)

    return out["messages"][-2].content
