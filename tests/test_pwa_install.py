import json
from pathlib import Path

def test_pwa_manifest():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / 'static/manifest.json').read_text(encoding='utf-8'))
    assert data['display'] == 'standalone'
    assert data['start_url'] == '/'
    assert (root / 'static/offline.html').exists()
