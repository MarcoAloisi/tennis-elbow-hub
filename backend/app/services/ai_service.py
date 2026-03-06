"""AI analysis service using OpenRouter API.

Provides tennis coaching insights by analyzing match statistics
through an LLM via the OpenRouter API.
"""

import json

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("services.ai")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _build_prompt(match_data: dict) -> str:
    """Build a detailed tennis coaching prompt from match data.

    Args:
        match_data: Dictionary containing match info and player stats.

    Returns:
        Formatted prompt string.
    """
    info = match_data.get("info", {})
    p1 = match_data.get("player1", {})
    p2 = match_data.get("player2", {})

    p1_name = p1.get("name", "Player 1")
    p2_name = p2.get("name", "Player 2")
    user_name = match_data.get("userName", p1_name)


    # Clean the payload to pass to the model
    clean_data = {
        "tournament_info": {
            "name": info.get("tournament", "Unknown"),
            "date": info.get("date", ""),
            "score": f"{p1_name} def. {p2_name} {info.get('score', 'N/A')}",
            "duration": info.get("duration", "N/A"),
        },
        "players": {
            p1_name: {
                "elo": info.get("player1_elo", "N/A"),
                "elo_change": info.get("player1_elo_diff", "N/A"),
                "serve": p1.get("serve", {}),
                "points": p1.get("points", {}),
                "rally": p1.get("rally", {}),
                "break_points": p1.get("break_points", {})
            },
            p2_name: {
                "elo": info.get("player2_elo", "N/A"),
                "elo_change": info.get("player2_elo_diff", "N/A"),
                "serve": p2.get("serve", {}),
                "points": p2.get("points", {}),
                "rally": p2.get("rally", {}),
                "break_points": p2.get("break_points", {})
            }
        }
    }

    prompt = f"""You are an elite tennis analyst and coach for professional players, analyzing a match from Tennis Elbow 4.
The user's player name is "{user_name}". Analyze this match strictly from their perspective.

<instructions>
  <phase_1_contextual_awareness>
    1. Determine Court Surface: Look at the 'Tournament' field. Infer the court surface immediately (e.g., Wimbledon = Grass, Roland Garros = Clay, US Open/Australian Open = Hard, Indoor = Carpet/Hard).
    2. Adjust Analysis by Surface:
      * Clay: Value consistency, break point conversion, and rally length over raw serve speed.
      * Grass: Value first serve percentage, net approaches, and shortness of points.
      * Hard: Look for a balance of aggression and movement.
      * Example: If the player hit many aces on Clay, highlight this as an exceptional feat. If they stayed back on Grass, criticize the lack of forward movement.
  </phase_1_contextual_awareness>

  <phase_2_statistical_interpretation>
    1. Volume vs. Efficiency (The 'Sample Size' Rule):
      * NEVER praise a stat based on percentage alone. You must check the volume (attempted vs total).
      * Scenario: If a player wins 6/6 net points (100%) but played 80 baseline points, they are NOT a "net rusher." They are a "baseliner who chooses their moments well."
      * Correction: Do not say "Perfect net play." Say "Excellent selectivity on rare net approaches."
      * Scenario: If a player has low unforced errors but very few winners, they are "passive/pushing," not "clinical."
    2. Connect the Dots:
      * Correlate Serve Speed with Points Won on First Serve. (Did the speed actually help?)
      * Correlate Break Points Converted with Mental Toughness.
  </phase_2_statistical_interpretation>
</instructions>

<match_data>
{json.dumps(clean_data, indent=2)}
</match_data>

<output_format>
Provide your analysis strictly as a JSON object matching the exact schema below. Do NOT wrap the JSON in markdown code blocks (e.g., no ```json). Return ONLY valid JSON.
{{
  "match_summary": "Write 2 short sentences summarizing the match narrative. Explicitly mention the Court Surface and how it influenced the match dynamics. Define the user's playstyle based on where the majority of points were played.",
  "strengths": [
    {{
      "title": "Short Title (e.g. First-serve effectiveness)",
      "explanation": "Concise explanation connecting the stat to the result/surface. Use specific numbers."
    }}
  ],
  "areas_for_improvement": [
    {{
      "title": "Short Title",
      "explanation": "Concise explanation indicating where volume was too low to be effective, or efficiency dropped."
    }}
  ],
  "tactical_insights": [
    {{
      "title": "Short Title",
      "explanation": "Concise tactical advice synthesizing the data with the court surface."
    }}
  ],
  "key_takeaways": [
    "One major focus for practice.",
    "One major focus for the next match strategy.",
    "(Optional) Mental or physical note."
  ]
}}
</output_format>"""

    return prompt


async def analyze_match(match_data: dict) -> str:
    """Analyze a match using OpenRouter AI.

    Args:
        match_data: Dictionary containing match info and player stats.

    Returns:
        AI-generated analysis text.

    Raises:
        ValueError: If OpenRouter API key is not configured.
        httpx.HTTPError: If the API request fails.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise ValueError("OpenRouter API key not configured. Add OPENROUTER_API_KEY to .env")

    prompt = _build_prompt(match_data)

    logger.info(f"Calling OpenRouter with model: {settings.openrouter_model}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://tenniselbowhub.live",
                "X-Title": "Tennis Elbow Hub",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 5500,
            },
        )

        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No response from AI model")

        return choices[0]["message"]["content"]
