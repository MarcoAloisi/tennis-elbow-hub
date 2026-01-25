"""Match analysis API endpoints.

Provides endpoints for uploading and analyzing match log HTML files.
"""

from fastapi import APIRouter, UploadFile

from app.core.logging import get_logger
from app.core.security import sanitize_filename, validate_upload_file
from app.models.match_stats import MatchAnalysisResponse
from app.services.analyzer import process_uploaded_file

logger = get_logger("api.match_analysis")
router = APIRouter(prefix="/analysis", tags=["Match Analysis"])


@router.post(
    "/upload",
    response_model=MatchAnalysisResponse,
    summary="Upload and analyze match log",
    description="Upload an HTML match log file and receive parsed statistics.",
)
async def upload_match_log(file: UploadFile) -> MatchAnalysisResponse:
    """Upload and analyze a match log HTML file.

    Args:
        file: The uploaded HTML file.

    Returns:
        Parsed match statistics or error details.
    """
    # Validate the uploaded file
    content = await validate_upload_file(file)

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename or "unknown.html")

    logger.info(f"Processing uploaded file: {safe_filename} ({len(content)} bytes)")

    # Process and analyze the file
    result = await process_uploaded_file(content, safe_filename)

    return result


@router.get(
    "/sample",
    response_model=MatchAnalysisResponse,
    summary="Get sample analysis",
    description="Returns a sample match analysis for testing purposes.",
)
async def get_sample_analysis() -> MatchAnalysisResponse:
    """Get a sample match analysis for testing.

    Returns:
        Sample match statistics.
    """
    from app.models.match_stats import (
        BreakPointStats,
        MatchInfo,
        MatchStats,
        PlayerMatchStats,
        PointStats,
        RallyStats,
        ServeStats,
    )

    sample_serve = ServeStats(
        first_serve_in=25,
        first_serve_total=40,
        first_serve_pct=62.5,
        aces=3,
        double_faults=1,
        fastest_serve_kmh=195.0,
        avg_first_serve_kmh=175.0,
        avg_second_serve_kmh=130.0,
    )

    sample_rally = RallyStats(
        short_rallies_won=15,
        short_rallies_total=30,
        normal_rallies_won=8,
        normal_rallies_total=15,
        long_rallies_won=3,
        long_rallies_total=5,
        avg_rally_length=4.5,
    )

    sample_points = PointStats(
        winners=12,
        forced_errors=5,
        unforced_errors=8,
        net_points_won=4,
        net_points_total=6,
        points_on_first_serve_won=20,
        points_on_first_serve_total=25,
        points_on_second_serve_won=8,
        points_on_second_serve_total=15,
        return_points_won=15,
        return_points_total=35,
        total_points_won=48,
    )

    sample_break = BreakPointStats(
        break_points_won=2,
        break_points_total=4,
        break_games_won=2,
        set_points_saved=0,
        match_points_saved=0,
    )

    sample_player = PlayerMatchStats(
        name="Sample Player",
        serve=sample_serve,
        rally=sample_rally,
        points=sample_points,
        break_points=sample_break,
    )

    return MatchAnalysisResponse(
        success=True,
        stats=MatchStats(
            info=MatchInfo(
                player1_name="Roger Federer",
                player2_name="Rafael Nadal",
                score="6-4 7-5",
                tournament="Sample Tournament",
                duration="1:45:00",
                real_duration="2:30:00",
            ),
            player1=sample_player,
            player2=PlayerMatchStats(
                name="Rafael Nadal",
                serve=sample_serve,
                rally=sample_rally,
                points=PointStats(
                    winners=10,
                    forced_errors=7,
                    unforced_errors=10,
                    net_points_won=2,
                    net_points_total=4,
                    points_on_first_serve_won=18,
                    points_on_first_serve_total=28,
                    points_on_second_serve_won=6,
                    points_on_second_serve_total=12,
                    return_points_won=12,
                    return_points_total=30,
                    total_points_won=42,
                ),
                break_points=BreakPointStats(
                    break_points_won=1,
                    break_points_total=3,
                    break_games_won=1,
                    set_points_saved=1,
                    match_points_saved=0,
                ),
            ),
        ),
        filename="sample_match.html",
    )
