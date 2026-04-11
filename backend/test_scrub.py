import asyncio
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from app.core.database import get_session_factory
from app.models.finished_match import FinishedMatch
from app.models.daily_stats import DailyStats

async def run():
    print("Starting data scrub analysis...")
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(FinishedMatch))
        matches = result.scalars().all()
        
        matches_to_delete = []
        for m in matches:
            total_games = 0
            if m.score:
                sets = m.score.split()
                for s in sets:
                    if "/" in s:
                        parts = s.split("/")
                        g1_str = "".join(c for c in parts[0] if c.isdigit())
                        g2_str = "".join(c for c in parts[1].split("(")[0] if c.isdigit())
                        if g1_str and g2_str:
                            try:
                                total_games += int(g1_str) + int(g2_str)
                            except ValueError:
                                pass
            if total_games < 5:
                matches_to_delete.append(m)
                
        print(f"Found {len(matches_to_delete)} incomplete matches (<5 games) out of {len(matches)} total.")
        
        # We won't delete yet. Just print some examples
        for m in matches_to_delete[:10]:
            print(f"- Date: {m.date}, Score: '{m.score}', Players: {m.match_name}")

if __name__ == "__main__":
    asyncio.run(run())
