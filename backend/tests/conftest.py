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


@pytest.fixture
def sample_spanish_match_html() -> str:
    """Sample Spanish match log HTML for testing analyzer.

    Uses 'vs' separator and includes '; Crc = ...' in ELO strings.

    Returns:
        HTML content string.
    """
    return """
    <html>
    <body>
    <p><input type="checkbox" onClick="SetVis(this, '-37549154')">alnicozu (ELO: 1606 +19 ; Crc = 13198898) vs Franky Franchicha (ELO: 1772 -19 ; Crc = 14394570) : 6/3 - AO Rod Laver Day - 0:10'47 (0:32'35) - 2026-01-23 16:00 [Online]</p>
    <table id="-37549154"><tr><td class="d1">19 / 28 = 68%</td><td class="c1">Primeros servicios</td><td class="d1">17 / 23 = 74%</td><td>&nbsp;</td>
    <td class="d2">22 / 39 = 56%</td><td class="c2">Rallies cortos ganados (< 5)</td><td class="d2">17 / 39 = 44%</td></tr>
    <tr><td class="d2">4</td><td class="c2">Aces</td><td class="d2">4</td><td>&nbsp;</td>
    <td class="d1">4 / 8 = 50%</td><td class="c1">Rallies normales ganados (5-8)</td><td class="d1">4 / 8 = 50%</td></tr>
    <tr><td class="d1">0</td><td class="c1">Doble faltas</td><td class="d1">1</td><td>&nbsp;</td>
    <td class="d2">4 / 4 = 100%</td><td class="c2">Rallies largos ganados (> 8)</td><td class="d2">0 / 4 = 0%</td></tr>
    <tr><td class="d2">197 Km/h</td><td class="c2">Servicio más rápido</td><td class="d2">191 Km/h</td><td>&nbsp;</td>
    <td class="d1"></td><td class="c1">Duración media del rally: 3.5</td><td class="d1"></td></tr>
    <tr><td class="d1">180 Km/h</td><td class="c1">Promedio de velocidad del 1° saque</td><td class="d1">182 Km/h</td><td>&nbsp;</td>
    <td class="d2">0</td><td class="c2">Puntos de set salvados</td><td class="d2">0</td></tr>
    <tr><td class="d2">152 Km/h</td><td class="c2">Promedio de velocidad del 2° saque</td><td class="d2">157 Km/h</td><td>&nbsp;</td>
    <td class="d1">0</td><td class="c1">Puntos de partido salvados</td><td class="d1">0</td></tr>
    <tr><td class="d1">9</td><td class="c1">Tiros ganadores</td><td class="d1">10</td><td>&nbsp;</td>
    <td class="d2">16 / 19 = 84%</td><td class="c2">Puntos ganados en el 1° servicio</td><td class="d2">13 / 17 = 76%</td></tr>
    <tr><td class="d2">2</td><td class="c2">Errores forzados</td><td class="d2">6</td><td>&nbsp;</td>
    <td class="d1">5 / 9 = 56%</td><td class="c1">Puntos ganados en el 2° servicio</td><td class="d1">1 / 6 = 17%</td></tr>
    <tr><td class="d1">5</td><td class="c1">Errores no forzados</td><td class="d1">10</td><td>&nbsp;</td>
    <td class="d2">9 / 23 = 39%</td><td class="c2">Puntos ganados sobre la devolución</td><td class="d2">7 / 28 = 25%</td></tr>
    <tr><td class="d2">0 / 0 = 0%</td><td class="c2">Puntos en la red</td><td class="d2">0 / 0 = 0%</td><td>&nbsp;</td>
    <td class="d1">1</td><td class="c1">Devoluciones ganadoras</td><td class="d1">0</td></tr>
    <tr><td class="d1">1 / 1 = 100%</td><td class="c1">Puntos de quiebre aprovechados</td><td class="d1">0 / 0 = 0%</td><td>&nbsp;</td>
    <td class="d2">1 / 1 = 100%</td><td class="c2">Quiebres / Juegos con puntos de quiebre</td><td class="d2">0 / 0 = 0%</td></tr>
    <tr><td class="d2">30</td><td class="c2">Total de puntos ganados</td><td class="d2">21</td></tr>
    </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_polish_match_html() -> str:
    """Sample Polish match log HTML for testing analyzer.

    Uses 'Przegrana' separator and Doubles format with Crc.

    Returns:
        HTML content string.
    """
    return """
    <html>
    <body>
    <p><input type="checkbox" onClick="SetVis(this, '-12345678')">POLAND (Crc = 7334370)) & Lleyton Hewitt (Crc = 3698732)) Przegrana Marcolino (Crc = 2225459)) & Bob Bryan (Crc = 13054943)) : 6/3 6/7(4) 6/3 - AO Rod Laver Night - 0:46'09 (2:13'07) - 2026-02-07 10:56 [Online]</p>
    <table id="-12345678"><tr><td class="d1">66 / 95 = 69%</td><td class="c1">Pierwszy serwis</td><td class="d1">64 / 101 = 63%</td><td>&nbsp;</td>
    <td class="d2">56 / 106 = 53%</td><td class="c2">SHORT RALLIES WON (< 5)</td><td class="d2">50 / 106 = 47%</td></tr>
    <tr><td class="d2">5</td><td class="c2">Asy</td><td class="d2">6</td><td>&nbsp;</td>
    <td class="d1">21 / 41 = 51%</td><td class="c1">MEDIUM RALLIES WON (5-8)</td><td class="d1">20 / 41 = 49%</td></tr>
    <tr><td class="d1">1</td><td class="c1">Podwójne błędy</td><td class="d1">1</td><td>&nbsp;</td>
    <td class="d2">31 / 49 = 63%</td><td class="c2">LONG RALLIES WON (> 8)</td><td class="d2">18 / 49 = 37%</td></tr>
    <tr><td class="d2">226 km/h</td><td class="c2">FASTEST SERVE</td><td class="d2">246 km/h</td><td>&nbsp;</td>
    <td class="d1"></td><td class="c1">AVERAGE RALLY LENGTH: 6.1</td><td class="d1"></td></tr>
    <tr><td class="d1">197 km/h</td><td class="c1">AVG 1st SERVE SPEED</td><td class="d1">202 km/h</td><td>&nbsp;</td>
    <td class="d2">0</td><td class="c2">SET POINTS SAVED</td><td class="d2">1</td></tr>
    <tr><td class="d2">161 km/h</td><td class="c2">AVG 2nd SERVE SPEED</td><td class="d2">167 km/h</td><td>&nbsp;</td>
    <td class="d1">0</td><td class="c1">MATCH POINTS SAVED</td><td class="d1">0</td></tr>
    <tr><td class="d1">54</td><td class="c1">Uderzenia wygrywajšce</td><td class="d1">38</td><td>&nbsp;</td>
    <td class="d2">49 / 66 = 74%</td><td class="c2">Punkty z pierwszego serwisu</td><td class="d2">40 / 64 = 63%</td></tr>
    <tr><td class="d2">20</td><td class="c2">FORCED ERRORS</td><td class="d2">18</td><td>&nbsp;</td>
    <td class="d1">19 / 29 = 66%</td><td class="c1">Punkty z drugiego serwisu</td><td class="d1">21 / 37 = 57%</td></tr>
    <tr><td class="d1">23</td><td class="c1">UNFORCED ERRORS</td><td class="d1">30</td><td>&nbsp;</td>
    <td class="d2">40 / 101 = 40%</td><td class="c2">RETURN POINTS WON</td><td class="d2">27 / 95 = 28%</td></tr>
    <tr><td class="d2">79 / 133 = 59%</td><td class="c2">Podejcia do siatki</td><td class="d2">56 / 129 = 43%</td><td>&nbsp;</td>
    <td class="d1">0</td><td class="c1">RETURN WINNERS</td><td class="d1">1</td></tr>
    <tr><td class="d1">3 / 7 = 43%</td><td class="c1">Przełamania</td><td class="d1">1 / 4 = 25%</td><td>&nbsp;</td>
    <td class="d2">3 / 4 = 75%</td><td class="c2">BREAKS / GAMES</td><td class="d2">1 / 1 = 100%</td></tr>
    <tr><td class="d2">108</td><td class="c2">Suma zdobytych punktów</td><td class="d2">88</td></tr>
    </table>
    </body>
    </html>
    """

