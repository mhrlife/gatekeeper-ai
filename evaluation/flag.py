import json
from dataclasses import dataclass
from datetime import datetime, timezone  # Added timezone
from typing import List, Dict, Any  # Added Any

from langgraph.func import entrypoint, task
from pydantic import BaseModel, Field
from typing_extensions import Literal, Optional, Tuple

from clients.openai import create_chat_client, MAIN_MODEL
from evaluation.context import LLMContext
from evaluation.prompt import FLAG_PROMPT, ACTION_PROMPT


@dataclass
class FlagContext(LLMContext):
    first_name: str
    message: str
    group_title: str
    group_context: str
    user_message_history: List[Dict[str, Any]]
    current_time: datetime


class FlagResponse(BaseModel):
    classification: Literal[
        "CLEAN", "SPAM", "SEXUAL", "ADVERTISEMENT", "FLIRT", "INSULT", "POLITICS", "IRRELEVANT_TO_GROUP"] = Field(
        description="The category this content falls into"
    )

    confidence: Literal["Low", "Medium", "High"] = Field(
        description="How confident the system is in this classification"
    )

    level: Literal["Low", "Medium", "High"] = Field(
        description="How serious the system thinks this classification is"
    )

    primary_evidence: Optional[str] = Field(
        default=None,
        description="Key evidence supporting this classification, only if not CLEAN. max length 20 characters",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation for why this content received this classification, only if not CLEAN.  max length 20 characters",
    )


class JudgmentResponse(BaseModel):
    user_account_action: Literal["DISMISS", "RESTRICT", "REMOVE", "BAN"] = Field(
        description="The determined action to take on the user's account"
    )

    user_message_action: Literal["DISMISS", "DELETE"] = Field(
        description="The determined action to take on the user's message"
    )

    reasoning: str = Field(
        description="Explanation of the decision-making process and justification for the severity assessment.  max length 20 characters",
    )

    message_to_user: Optional[str] = Field(
        default=None,
        description=(
            "Suggested message to send to the user explaining the action (if applicable).  max length 40 characters\n"
            "MUST BE IN THE SAME LANGUAGE AS THE INPUT MESSAGE\n"
            "give them also feedback how they can stay in the groups rules\n"
            "You Must always give them a feedback how they can stay in the groups rules\n"
        ),
    )


async def associate_flag(first_name: str, message: str, group_title: str, group_context: str,
                         user_message_history: List[Dict[str, Any]], current_time: datetime) -> Tuple[
    FlagResponse, Optional[JudgmentResponse]]:
    return await flag.ainvoke({
        "first_name": first_name,
        "message": message,
        "group_title": group_title,
        "group_context": group_context,
        "user_message_history": user_message_history,
        "current_time": current_time.isoformat(),  # Pass as ISO string
    })


@entrypoint()
async def flag(
        args: dict,
) -> Tuple[FlagResponse, Optional[JudgmentResponse]]:
    """
    This function is used to flag sensitive contents
    """
    current_time_arg = args.get("current_time")
    if current_time_arg:
        # Ensure it's timezone-aware if it's coming as a string
        parsed_time = datetime.fromisoformat(current_time_arg)
        if parsed_time.tzinfo is None:
            parsed_time = parsed_time.replace(tzinfo=timezone.utc)  # Assume UTC if no tz info
    else:
        parsed_time = datetime.now(timezone.utc)

    ctx = FlagContext(
        llm=create_chat_client(MAIN_MODEL),
        message=args.get("message"),
        first_name=args.get("first_name"),
        group_title=args.get("group_title"),
        group_context=args.get("group_context"),
        user_message_history=args.get("user_message_history", []),
        current_time=parsed_time
    )

    flag_response: FlagResponse = await initial_flag_content(ctx)
    if flag_response.classification == "CLEAN":
        return flag_response, None

    judgement_response = await judgement(ctx, flag_response)

    return flag_response, judgement_response


@task
async def initial_flag_content(ctx: FlagContext) -> FlagResponse:
    """
    This function is used to flag sensitive contents
    """
    history_str_parts = []
    for msg_data in ctx.user_message_history:
        part = f"- At {msg_data['created_at']}: \"{msg_data['text']}\""
        if msg_data.get('replied_to_text') and msg_data['replied_to_text'] is not None:  # Check for None
            part += f" (in reply to: \"{msg_data['replied_to_text']}\")"
        history_str_parts.append(part)

    user_message_history_str = "\n".join(
        history_str_parts) if history_str_parts else "No recent message history available for this user in this group."

    result = await ctx.llm.with_structured_output(
        schema=FlagResponse,
        strict=True
    ).ainvoke(
        FLAG_PROMPT.format(
            FIRST_NAME=ctx.first_name,
            INPUT=ctx.message,
            GROUP_TITLE=ctx.group_title,
            GROUP_CONTEXT=ctx.group_context,
            USER_MESSAGE_HISTORY=user_message_history_str,
            CURRENT_TIME=ctx.current_time.isoformat()  # Ensure current_time is also passed
        )
    )

    return result


@task
async def judgement(ctx: FlagContext, flag_response: FlagResponse) -> JudgmentResponse:
    """
    This function is used to flag sensitive contents
    """
    # The judgement prompt does not currently use user_message_history or current_time directly,
    # but they are available in ctx if needed in the future.
    # WardenAI's analysis (which might be influenced by history) is passed.
    result = await ctx.llm.with_structured_output(
        schema=JudgmentResponse,
        strict=True
    ).ainvoke(
        ACTION_PROMPT.format(
            FIRST_NAME=ctx.first_name,
            INPUT=ctx.message,
            WARDEN_ANALYSIS=json.dumps(flag_response.model_dump(), indent=2, ensure_ascii=False),
            GROUP_TITLE=ctx.group_title,
            GROUP_CONTEXT=ctx.group_context,
        )
    )

    return result
