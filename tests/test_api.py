import asyncio
import httpx
from main import app

BASE = {
    'question': 'Позвонит ли коллега в ближайшие две недели?',
    'topic': 'contact', 'city': 'minsk',
    'datetime': '2026-10-26T12:00', 'horizon_days': 14,
}

def run_request(method, url, json=None):
    async def invoke():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
            return await client.request(method, url, json=json)
    return asyncio.run(invoke())

def test_homepage_served():
    result = run_request('GET', '/')
    assert result.status_code == 200
    assert 'id="calculate"' in result.text
    assert 'id="target_house"' in result.text
    assert 'id="horizon"' in result.text
    assert 'id="export"' in result.text

def test_config_and_health():
    config = run_request('GET', '/api/config')
    assert config.status_code == 200
    assert len(config.json()['houses']) == 12
    assert 'minsk' in config.json()['cities']
    assert run_request('GET', '/api/health').json()['version'] == '0.5.0'

def test_calculate_and_horizon():
    resp = run_request('POST', '/api/horary', json=BASE)
    assert resp.status_code == 200, resp.text
    info=resp.json()
    assert info['horizon_days'] == 14
    assert info['significators']['house'] == 7
    assert info['utc_time'].startswith('2026-10-26T09:00')
    assert info['moon_next'] is not None
    assert info['evidence']

def test_custom_house_and_city():
    resp = run_request('POST', '/api/horary', json={**BASE,
        'city': 'other', 'city_name': 'Гродно', 'lat': 53.68, 'lon': 23.83, 'tz': 'Europe/Minsk',
        'target_house': 5})
    assert resp.status_code == 200
    assert resp.json()['city'] == 'Гродно'
    assert resp.json()['significators']['house'] == 5

def test_errors_are_user_friendly():
    cases = [
        ({**BASE,'question':'да'}, 'вопрос'),
        ({**BASE,'city':'other','lat':0,'lon':0,'tz':'Bogus/Zone'}, 'часовой'),
        ({**BASE,'horizon_days':0}, 'Срок'),
        ({**BASE,'target_house':13}, 'Дом'),
        ({**BASE,'city':'berlin','datetime':'2026-03-29T02:30'}, 'не существует'),
    ]
    for data,expected in cases:
        r = run_request('POST','/api/horary',json=data)
        assert r.status_code == 422, (data,r.text)
        assert expected.lower() in r.json()['detail'].lower()


def test_simple_answer_api_and_light_layout():
    r=run_request('POST','/api/horary',json=BASE)
    assert r.status_code == 200
    data=r.json()
    assert data['simple_answer']['summary']
    assert data['simple_answer']['label']
    page=run_request('GET','/').text
    assert 'id="simple-label"' in page
    assert 'id="expert"' in page
    assert '--bg:#f7f7f4' in page
