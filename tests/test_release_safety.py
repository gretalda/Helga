from pathlib import Path
from main import app
import asyncio
import httpx

ROOT = Path(__file__).resolve().parents[1]

def request(method, url):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, url)
    return asyncio.run(run())

def test_personal_api_responses_are_not_cached():
    for path in ("/", "/api/health", "/api/config"):
        response = request("GET", path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"

def test_history_is_opt_in_and_offline_is_explicit():
    page = (ROOT / "static/index.html").read_text(encoding="utf-8")
    assert 'id="remember-history"' in page
    assert "if(!$('remember-history').checked)return" in page
    sw = (ROOT / "static/service-worker.js").read_text(encoding="utf-8")
    assert "url.pathname.startsWith('/api/')" in sw
    assert (ROOT / "static/offline.html").exists()
