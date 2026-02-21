import asyncio
from sqlalchemy import select
from app.core.database import get_session_factory
from app.models.finished_match import FinishedMatch

async def main():
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(FinishedMatch))
        matches = result.scalars().all()
        print(f"Total ALL matches: {len(matches)}")
        from collections import Counter
        dates = Counter(m.date.isoformat() for m in matches if m.date)
        print("Dates:", dates.most_common(10))

if __name__ == "__main__":
    asyncio.run(main())
