import pytest
from horary import (dignity_lords, dignity_profile, full_reception_analysis,
                    calculate, PTOLEMAIC_TERMS, RECEPTION_WEIGHT)

def snapshot(a,b,la,lb):
    return {a:{'longitude':la},b:{'longitude':lb}}

def test_all_terms_cover_full_sign_without_gaps():
    assert len(PTOLEMAIC_TERMS)==12
    for entries in PTOLEMAIC_TERMS:
        assert len(entries)==5 and entries[-1][1]==30
        assert all(x[1] < y[1] for x,y in zip(entries,entries[1:]))
        for i in range(30):
            assert len([name for name,end in entries if i < end]) >= 1

def test_decan_chaldean_aries_taurus_boundaries():
    assert dignity_lords(0,True)['декан']=='Марс'
    assert dignity_lords(9.999,True)['декан']=='Марс'
    assert dignity_lords(10,True)['декан']=='Солнце'
    assert dignity_lords(20,True)['декан']=='Венера'
    assert dignity_lords(30,True)['декан']=='Меркурий'
    assert dignity_lords(40,True)['декан']=='Луна'

def test_lilly_ptolemaic_terms_boundaries():
    assert dignity_lords(5.99,True)['терм']=='Юпитер'
    assert dignity_lords(6,True)['терм']=='Венера'
    assert dignity_lords(13.999,True)['терм']=='Венера'
    assert dignity_lords(14,True)['терм']=='Меркурий'
    assert dignity_lords(30,True)['терм']=='Венера'

def test_day_night_triplicity_differ_and_water_is_mars():
    assert dignity_lords(5,True)['триплицитет']=='Солнце'
    assert dignity_lords(5,False)['триплицитет']=='Юпитер'
    assert dignity_lords(45,True)['триплицитет']=='Венера'
    assert dignity_lords(45,False)['триплицитет']=='Луна'
    assert dignity_lords(100,True)['триплицитет']=='Марс'
    assert dignity_lords(100,False)['триплицитет']=='Марс'

def test_mutual_domicile_reception_symmetry():
    # Mars in Libra (Venus domicile); Venus in Aries (Mars domicile).
    result=full_reception_analysis('Марс','Венера',snapshot('Марс','Венера',180,0),True)
    assert result['mutual']
    assert all('обитель' in x['positive'] for x in result['directions'])
    assert 'изгнание' not in result['directions'][0]['positive']

def test_one_sided_only_when_one_host_in_other_dignity():
    result=full_reception_analysis('Марс','Венера',snapshot('Марс','Венера',180,60),True)
    assert not result['mutual']
    assert result['directions'][0]['positive']==['обитель']
    assert result['directions'][1]['positive']==[]

def test_detriment_is_not_positive_reception():
    out=full_reception_analysis('Марс','Венера',snapshot('Марс','Венера',210,60),True)
    assert 'изгнание' in out['directions'][0]['negative']
    assert 'изгнание' not in out['directions'][0]['positive']

def test_identical_rulers_no_mutual_self_reception():
    same=full_reception_analysis('Марс','Марс',{'Марс':{'longitude':120}},True)
    assert same['mutual'] is False and same['directions']==[]

def test_dignity_profile_exile_score():
    venus=dignity_profile('Венера',5,True)
    assert 'изгнание' in venus['weaknesses']
    assert venus['score']<0

def test_api_exposes_reception_calculation_not_waiting_for_manual_check():
    result=calculate({'question':'Позвонит ли мне бывший муж в течение 2 недель?',
                      'city':'minsk','datetime':'2026-10-26T12:00'})
    report=result['reception_analysis']
    assert report['sect'] in ('дневная','ночная')
    assert len(report['directions'])==2
    assert len(report['profiles'])==2
    assert all(set(d['rulers'])==set(RECEPTION_WEIGHT)|{'изгнание','падение'} for d in report['profiles'].values())
    assert not any('нужно проверить рецепции' in r.lower() for r in result['simple_answer']['reasons'])
    assert any('Рецепции:' in s for s in result['simple_answer']['reasons'])

def test_frontend_has_reception_table():
    from pathlib import Path
    html=(Path(__file__).parents[1]/'static'/'index.html').read_text()
    for element in ('rec-summary','rec-scores','rec-rows','rec-note'):
        assert f'id="{element}"' in html

def test_full_reception_matrix_42_directions():
    from horary import chart_reception_matrix, PLANET_IDS
    planets={name:{'longitude':i*47.7} for i,name in enumerate(PLANET_IDS)}
    chart=chart_reception_matrix(planets,True)
    assert chart['checks']==42
    assert len(chart['directions'])==42
    assert len(chart['profiles'])==7
    assert all(x['guest']!=x['receiver'] for x in chart['directions'])
    assert all(x in chart['directions'] for x in chart['positive'])

def test_full_matrix_in_real_api():
    r=calculate({'question':'Позвонит ли бывший муж завтра?','city':'minsk','datetime':'2026-10-26T12:00'})
    assert r['all_receptions']['checks']==42
    assert len(r['all_receptions']['profiles'])==7
