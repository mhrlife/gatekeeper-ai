import os

from tortoise import Tortoise


async def init_db():
    db_url = os.getenv("DB_CONNECTION")

    await Tortoise.init(db_url=db_url, modules={"models": ["database.models"]})
    await Tortoise.generate_schemas()
