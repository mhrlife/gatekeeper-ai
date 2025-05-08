import asyncio

from evaluation.flag import flag


async def run():
    result = await flag.ainvoke({
        "first_name": "Ali",
        "message": """جنده خونه‌ی علی
        
سلام من جنده خونه راه انداختم بیاید پی وی"""
    })

    print(result[0])
    print(result[1])


if __name__ == "__main__":
    asyncio.run(
        run()
    )
