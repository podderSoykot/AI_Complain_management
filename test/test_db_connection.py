import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import get_settings


async def main() -> None:
    settings = get_settings()
    base_url = settings.database_url
    candidates = [base_url]
    if "sslmode=require" in base_url:
        candidates.append(base_url.replace("sslmode=require", "ssl=require"))
        candidates.append(base_url.replace("sslmode=require", "ssl=true"))

    for idx, url in enumerate(candidates, start=1):
        masked = url.split("@")[-1] if "@" in url else url
        print(f"[Try {idx}] Loaded DB host part: {masked}")
        try:
            engine = create_async_engine(url, pool_pre_ping=True)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                print(f"[Try {idx}] SELECT 1 result: {result.scalar_one()}")
            await engine.dispose()
            print(f"[Try {idx}] SUCCESS")
            return
        except Exception as exc:
            print(f"[Try {idx}] FAILED: {exc}")

    raise RuntimeError("All URL variants failed")


if __name__ == "__main__":
    asyncio.run(main())
