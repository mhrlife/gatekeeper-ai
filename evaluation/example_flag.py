import asyncio

from evaluation.flag import flag


async def run():
    result = await flag.ainvoke({
        "first_name": "Ali",
        "message": """یک حرف خیلی خیلی زشت""",
        "group_title": "Test Group",
        "group_context": "Rule 1: Be nice. Rule 2: No spam."
    })

    print(result[0])
    if result[1]: 
        print(result[1])


if __name__ == "__main__":
    asyncio.run(
        run()
    )
