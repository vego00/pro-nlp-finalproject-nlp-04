import asyncio
from alembic import context
from storage.database import get_engine, metadata

def run(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()

async def main():
    engine = get_engine()
    async with engine.connect() as connection:
        await connection.run_sync(run)
    await engine.dispose()

asyncio.run(main())
