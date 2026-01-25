"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application.

    Yields:
        TestClient instance.
    """
    return TestClient(app)


@pytest.fixture
def sample_server_data() -> str:
    """Sample server data for testing parser.

    Returns:
        Raw server data string.
    """
    return (
        '0 E9FD "RBI vs TestPlayer" 1B198E41 96 415 3 "XKT v4.2d" '
        '"6/3 4/6 1/1 -- 00:40•" 393 0 1 "BlueGreenCement" 69760194'
    )


@pytest.fixture
def sample_match_html() -> str:
    """Sample match log HTML for testing analyzer.

    Returns:
        HTML content string.
    """
    return """
    <html>
    <body>
    <p>Roger Federer (ELO: 1500 +30) def. Rafael Nadal (ELO: 1450 -30) : 6/4 7/5 - Test Tournament - 1:45:00 (2:30:00) - 2024-01-15 14:30</p>
    <table>
        <tr>
            <td>41 / 66 = 62%</td>
            <td>1ST SERVE %</td>
            <td>45 / 79 = 57%</td>
        </tr>
        <tr>
            <td>6</td>
            <td>ACES</td>
            <td>20</td>
        </tr>
        <tr>
            <td>1</td>
            <td>DOUBLE FAULTS</td>
            <td>1</td>
        </tr>
        <tr>
            <td>222 Km/h</td>
            <td>FASTEST SERVE</td>
            <td>243 Km/h</td>
        </tr>
        <tr>
            <td>36</td>
            <td>WINNERS</td>
            <td>20</td>
        </tr>
        <tr>
            <td>79</td>
            <td>TOTAL POINTS WON</td>
            <td>66</td>
        </tr>
    </table>
    </body>
    </html>
    """
