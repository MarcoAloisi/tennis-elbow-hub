import asyncio
from sqlalchemy import select
from datetime import date
from app.core.database import get_session_factory
from app.models.finished_match import FinishedMatch

async def main():
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(FinishedMatch).where(FinishedMatch.date >= date(2026, 2, 1)))
        matches = result.scalars().all()
        print(f"Total matches: {len(matches)}")
        
        valid_players = []
        for match in matches:
            name = match.match_name
            if not name: continue
            if " vs " in name:
                p1, p2 = name.split(" vs ", 1)
                p1, p2 = p1.strip(), p2.strip()
                if p1 != "1210967164" and p1 != "Unknown": valid_players.append(p1)
                if p2 != "1210967164" and p2 != "Unknown": valid_players.append(p2)
            else:
                name = name.strip()
                if name != "1210967164" and name != "Unknown": valid_players.append(name)
                
        print(f"Valid player occurrences: {len(valid_players)}")
        from collections import Counter
        counts = Counter(valid_players)
        print("Top 10 players:", counts.most_common(10))

if __name__ == "__main__":
    asyncio.run(main())
