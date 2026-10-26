"""Deterministic integrated forecast checks. No success rate is inferred."""
from datetime import date
from fastapi.testclient import TestClient
from main import app
from integrated_forecast import active_solar, merge_sources
import astro_portal as portal

CLIENT=TestClient(app)
PROFILE={'birth_date':'1987-07-29','birth_time':'18:00','city':'minsk','time_known':True}

def request(start='2026-10-26',end='2026-11-30',**kwargs):
    return CLIENT.post('/api/astro/report',json={'mode':'integrated','profile':PROFILE,'date':start,'end_date':end,**kwargs})

def test_report_is_cross_method_and_cites_individual_sources():
    r=request();assert r.status_code==200,r.text
    x=r.json();assert x['type']=='integrated'
    assert x['method_report'].keys()>={'solar','lunar','direction','progression'}
    assert any(t['agreement']>=2 for t in x['themes'])
    assert all(t['agreement']==len(set(e['method'] for e in t['evidence'])&{'solar','progression','direction','transit'}) for t in x['themes'])
    assert 'вероятность' in x['lead']
    assert any('прогрессии и дирекции' in s['title'].lower() for s in x['sections'])
    assert any('Отношения' in s['title'] for s in x['sections'])
    assert x['zet_reference']['natal_positions']['Солнце']>=0
    assert 'перевод' not in x['title'].lower()
    assert x['validation'] is None

def test_active_solar_before_birthday_is_previous_cycle():
    prior=active_solar(PROFILE,date(2026,1,8))
    after=active_solar(PROFILE,date(2026,8,2))
    assert '2025' in prior['highlights'][0]['value']
    assert '2026' in after['highlights'][0]['value']

def test_timing_window_range_and_missing_birth_time():
    too_long=request('2026-01-01','2026-12-31')
    assert too_long.status_code==422
    unknown=CLIENT.post('/api/astro/report',json={'mode':'integrated','profile':{**PROFILE,'time_known':False},'date':'2026-10-26','end_date':'2026-11-01'})
    assert unknown.status_code==422
    assert 'время рождения' in unknown.json()['detail']

def test_historical_checks_count_both_matches_and_failures():
    past=[{'date':'2022-04-16','theme':'work','description':'смена деятельности'},
          {'date':'2020-12-11','theme':'love','description':'изменение отношений'}]
    controls=[{'date':'2022-05-01','theme':'work','description':''}]
    r=request(end='2026-10-29',past_events=past,control_dates=controls)
    assert r.status_code==200,r.text
    v=r.json()['validation']
    assert len(v['entries'])==3
    assert v['summary']['events']==2 and v['summary']['controls']==1
    assert 'ложные' in v['methodology']
    assert sum(v['summary'][k] for k in ('event_multiple','event_missing'))<=2
    assert all('method_count' in z and 'matched_methods' in z for z in v['entries'])

def test_event_errors_are_not_silently_reinterpreted():
    r=request(past_events=[{'date':'2027-01-20','theme':'love','description':'ещё не произошло'}])
    assert r.status_code==422
    r=request(past_events=[{'date':'2020-01-01','theme':'invalid','description':'какое-то событие'}])
    assert r.status_code==422

def test_empty_historical_input_does_not_claim_success():
    r=request();x=r.json()
    assert x['validation'] is None
    assert 'не выполнена' in x['sections'][-1]['title']

def test_all_new_form_controls_and_api_mode_present():
    html=CLIENT.get('/').text
    for text in ('Комплексный прогноз','past-events','control-dates','parseHistory','integrated'):
        assert text in html
    assert 'integrated' in CLIENT.get('/api/astro/config').json()['modes']
    assert CLIENT.get('/api/health').json()['version']=='1.2.0'