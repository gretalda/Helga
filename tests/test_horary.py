from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import pytest
from horary import calculate, RULERS, sign_index

BASE={'question':'Позвонит ли мне человек в ближайшие две недели?', 'topic':'contact', 'city':'minsk', 'datetime':'2026-10-26T08:49'}

def test_basic_horary():
    result=calculate(BASE)
    assert len(result['cusps'])==12
    assert len(result['planets'])==7
    assert result['utc_time'].startswith('2026-10-26T05:49')
    assert result['significators']['self']==RULERS[sign_index(result['asc'])]
    assert result['significators']['subject']==RULERS[sign_index(result['cusps'][6]['longitude'])]
    assert all(0 <= p['longitude'] < 360 for p in result['planets'].values())

def test_berlin_winter_timezone():
    result=calculate({**BASE,'city':'berlin','datetime':'2026-11-26T09:00'})
    assert result['utc_time'].startswith('2026-11-26T08:00')

def test_nonexistent_spring_clock_time():
    with pytest.raises(ValueError,match='не существует'):
        calculate({**BASE,'city':'berlin','datetime':'2026-03-29T02:30'})

def test_custom_invalid_tz():
    with pytest.raises(ValueError,match='часовой пояс'):
        calculate({**BASE,'city':'other','city_name':'Тест','lat':52.0,'lon':13.0,'tz':'Invalid/Zone'})

def test_theme_checks():
    for name in ['relationship','work','money']:
        assert calculate({**BASE,'topic':name})['topic']

def test_explicit_horizon_changes_conclusion_without_changing_positions():
    base = {**BASE, 'datetime': '2026-10-26T12:00'}
    short = calculate({**base,'horizon_days':14})
    long = calculate({**base,'horizon_days':45})
    assert short['asc'] == long['asc']
    assert short['planets'] == long['planets']
    if long['future_main_aspect'] and long['future_main_aspect']['days'] > 14:
        assert short['grade'] == 'neutral'


def test_future_perfection_is_exact_astronomically():
    from horary import PLANET_IDS, RULERS, sign_index
    import swisseph as swe
    r=calculate({**BASE,'datetime':'2026-10-26T12:00'})
    aspect=r['future_main_aspect']
    if aspect:
        a=PLANET_IDS[r['significators']['self']]
        b=PLANET_IDS[r['significators']['subject']]
        jd=r['jd']+aspect['days']
        lon_a=swe.calc_ut(jd,a,swe.FLG_MOSEPH)[0][0]
        lon_b=swe.calc_ut(jd,b,swe.FLG_MOSEPH)[0][0]
        from horary import angular_distance
        assert abs(angular_distance(lon_a,lon_b)-aspect['angle']) < 0.03
