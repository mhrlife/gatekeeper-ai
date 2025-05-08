import json
from dataclasses import dataclass

from pydantic import BaseModel, Field
from typing_extensions import Literal, Optional, Tuple

from langgraph.func import entrypoint, task

from clients.openai import create_chat_client, MAIN_MODEL
from evaluation.context import LLMContext
from evaluation.prompt import FLAG_PROMPT, ACTION_PROMPT


@dataclass
class FlagContext(LLMContext):
    first_name: str
    message: str


class FlagResponse(BaseModel):
    classification: Literal["CLEAN", "SPAM", "SEXUAL", "ADVERTISEMENT", "FLIRT", "INSULT", "POLITICS"] = Field(
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
    severity_assessment: Literal["DISMISS", "CAUTION", "WARNING", "RESTRICT", "REMOVE", "BAN"] = Field(
        description="The determined severity level and appropriate action to take"
    )

    reasoning: str = Field(
        description="Explanation of the decision-making process and justification for the severity assessment.  max length 20 characters",
    )

    message_to_user: Optional[str] = Field(
        default=None,
        description="Suggested message to send to the user explaining the action (if applicable).  max length 20 characters",
    )


async def associate_flag(first_name: str, message: str) -> Tuple[FlagResponse, JudgmentResponse]:
    return await flag.ainvoke({
        "first_name": first_name,
        "message": message,
    })

@entrypoint()
async def flag(
        args: dict,
) -> [FlagResponse, JudgmentResponse]:
    """
    This function is used to flag sensitive contents
    """
    ctx = FlagContext(
        llm=create_chat_client(MAIN_MODEL),
        message=args.get("message"),
        first_name=args.get("first_name"),
    )

    flag_response: FlagResponse = await initial_flag_content(ctx)
    if flag_response.classification == "CLEAN":
        return [flag_response, None]

    judgement_response = await judgement(ctx, flag_response)

    return [flag_response, judgement_response]


@task
async def initial_flag_content(ctx: FlagContext) -> FlagResponse:
    """
    This function is used to flag sensitive contents
    """
    result = await ctx.llm.with_structured_output(
        schema=FlagResponse,
        strict=True
    ).ainvoke(
        FLAG_PROMPT.format(
            FIRST_NAME=ctx.first_name,
            INPUT=ctx.message,
        )
    )

    return result


@task
async def judgement(ctx: FlagContext, flag_response: FlagResponse) -> JudgmentResponse:
    """
    This function is used to flag sensitive contents
    """
    result = await ctx.llm.with_structured_output(
        schema=JudgmentResponse,
        strict=True
    ).ainvoke(
        ACTION_PROMPT.format(
            FIRST_NAME=ctx.first_name,
            INPUT=ctx.message,
            WARDEN_ANALYSIS=json.dumps(flag_response.dict(), indent=2, ensure_ascii=False),
        )
    )

    return result
