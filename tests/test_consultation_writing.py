"""Regression checks for evidence-backed reader-facing forecasts."""
from datetime import date
from fastapi.testclient import TestClient
from main import app

client=TestClient(app)
p1={'birth_date':'1987-07-29','birth_time':'18:00','city':'minsk','time_known':True}
p2={'birth_date':'1990-02-14','birth_time':'10:30','city':'minsk','time_known':True}

def report(mode, profile=p1, date_='2026-10-26', **extra):
    r=client.post('/api/astro/report',json={'mode':mode,'profile':profile,'date':date_,**extra})
    assert r.status_code==200,r.text
    return r.json()

def test_all_forecast_methods_have_actual_life_sections():
    for mode,kwargs in [('solar',{'solar_year':2026}),('lunar',{}),('transits',{}),('day',{}),('period',{'end_date':'2026-11-04'}),('progression',{}),('direction',{})]:
        x=report(mode,**kwargs)
        full=' '.join(y['body'] for y in x['sections'])
        assert len(full)>1500,mode
        assert 'Отношения' in ' '.join(y['title'] for y in x['sections']),mode
        assert any('Работа' in y['title'] or 'Рабочие' in y['title'] for y in x['sections']),mode
        assert 'символ' in (full+x['note']).lower(),mode
        assert x['lead'] and x['sections'][0]['body']
        assert x['chart']['planets']
        assert 'Готовый' not in full

def test_solar_and_lunar_texts_differ_with_cycle_and_natal():
    s1=report('solar',solar_year=2026)
    s2=report('solar',solar_year=2027)
    m=report('lunar')
    other=report('solar',profile=p2,solar_year=2026)
    assert s1['lead']!=s2['lead']
    assert s1['lead']!=other['lead']
    assert s1['lead']!=m['lead']
    assert '2027' in s1['lead']
    assert '2027' in s2['lead']
    assert s1['return_chart']['planets']
    assert any('натальн' in v['title'].lower() or 'натальн' in v['body'].lower() for v in s1['sections'])

def test_transit_distinguishes_different_dates_and_profiles():
    a=report('transits')
    b=report('transits',date_='2026-12-15')
    c=report('transits',profile=p2)
    assert (a['lead'],a['sections'][1]['body'])!=(b['lead'],b['sections'][1]['body'])
    assert a['lead']!=c['lead'] or a['sections'][1]['body']!=c['sections'][1]['body']
    assert any('фон' in v['title'].lower() for v in a['sections'])
    assert any('Когда' in v['title'] for v in a['sections'])

def test_directed_and_progressed_are_not_confused():
    a=report('progression')
    b=report('direction')
    assert 'Прогрессивное Солнце' in a['lead']
    assert 'Символическая дуга' in b['lead']
    assert 'Прогрессивная Луна' in a['lead']
    assert 'Направленный Асцендент' in b['lead']
    assert a['overlay']!=b['overlay']

def test_unknown_time_does_not_infer_lunar_or_asc_in_progressions():
    x=report('progression',profile={**p1,'time_known':False})
    assert 'Луна' not in x['overlay']
    assert 'Без точного времени рождения' in x['lead']
    d=report('direction',profile={**p1,'time_known':False})
    assert 'ASC' not in d['overlay']
    assert 'MC' not in d['overlay']

def test_frontend_places_reading_before_technical_map():
    html=client.get('/').text
    start=html.index('function showReport(data)')
    segment=html[start:html.index('async function run()',start)]
    assert segment.index('for(const section')<segment.index('if(data.chart)')
    assert 'Показать карту' in segment
    assert 'id="install-app"' in html

def test_empty_evidence_is_not_invented_by_editorial_engine():
    import forecast_writer as f
    assert 'нет' in f._domain_scenes([]).lower()
    assert 'не' in f._render_overview([],'месяца').lower()
    assert 'не' in f._calendar_story([],'2026-10-26','две недели').lower()