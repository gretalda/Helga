"""Contract checks for the existing portal's public entry links and metadata.

These are offline checks. They never contact Telegram, Render or users.
"""
from pathlib import Path


PAGE = (Path(__file__).resolve().parents[1] / "static" / "portal.html").read_text(encoding="utf-8")


def test_public_version_matches_astro_api():
    assert 'id="status">Личный астролог · версия 1.2' in PAGE


def test_search_description_is_specific_and_not_predictive():
    assert '<meta name="description"' in PAGE
    assert 'Натальная карта' in PAGE
    assert 'не гарантия событий' in PAGE


def test_free_bot_referral_is_safe_and_trackable():
    assert 'https://t.me/AstroLichnoBot?start=day_web_portal_01' in PAGE
    assert 'rel="noopener noreferrer"' in PAGE
    assert 'Бесплатный прогноз в Telegram' in PAGE


def test_existing_horary_and_portal_buttons_are_preserved():
    assert 'href="/horary"' in PAGE
    assert 'id="run"' in PAGE
