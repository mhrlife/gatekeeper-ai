import asyncio

from evaluation.flag import flag


async def run():
    result = await flag.ainvoke({
        "first_name": "Ali",
        "message": """یک حرف خیلی خیلی زشت"""
    })

    print(result[0])
    print(result[1])


if __name__ == "__main__":
    asyncio.run(
        run()
    )
