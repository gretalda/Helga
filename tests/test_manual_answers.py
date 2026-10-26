from fastapi.testclient import TestClient
from main import app
from horary import calculate
from question_context import resolve_two_people
from pathlib import Path

c=TestClient(app)
BASE={'city':'minsk','datetime':'2026-10-26T11:00'}
Q='Как будут складываться отношения у Вики с Александром?'


def test_manual_first_person_needs_description_and_house():
    request={'first_role':'other','first_house':9,'relation_to_first':'spouse'}
    r=c.post('/api/horary',json={**BASE,'question':Q,'people_context':request})
    assert r.status_code==422 and '«Вручную»' in r.json()['detail']['message']
    request['first_role_text']='моя двоюродная родственница'
    r=c.post('/api/horary',json={**BASE,'question':Q,'people_context':request})
    assert r.status_code==200
    assert (r.json()['actor_house'],r.json()['significators']['house'])==(9,3)
    assert 'двоюродная' in r.json()['scope']


def test_manual_relation_to_first_has_free_text_and_derivative_house():
    payload={'first_role':'friend','relation_to_first':'other','relation_text':'соседка её мужа','relation_house':4}
    r=c.post('/api/horary',json={**BASE,'question':Q,'people_context':payload})
    assert r.status_code==200,r.text
    data=r.json()
    assert (data['actor_house'], data['significators']['house'])==(11,2)
    assert 'соседка её мужа' in data['scope']


def test_manual_relation_to_querent_second_person():
    payload={'first_role':'friend','second_role':'other','second_role_text':'бывшая соседка по подъезду','second_house':12}
    r=c.post('/api/horary',json={**BASE,'question':Q,'people_context':payload})
    assert r.status_code==200,r.text
    assert (r.json()['actor_house'], r.json()['significators']['house'])==(11,12)


def test_unknown_single_focus_manual_requires_text_and_house():
    q='Получится ли задуманное дело?'
    r=c.post('/api/horary',json={**BASE,'question':q,'focus_choice':'other','target_house':9})
    assert r.status_code==422
    r=c.post('/api/horary',json={**BASE,'question':q,'focus_choice':'other','target_house':9,'manual_focus_text':'поступление на курсы'})
    assert r.status_code==200,r.text
    assert 'поступление на курсы' in r.json()['scope']


def test_direction_answer_is_not_generic_and_mentions_people():
    q='Как будут складываться отношения у моей подруги Вики с её мужем Александром?'
    ans=calculate({**BASE,'question':q})['simple_answer']
    assert ans['label']!='Тема может получить развитие'
    assert 'Вики' in ans['summary'] and 'Александром' in ans['summary']
    assert 'Рецепции:' in ' '.join(ans['reasons'])


def test_breakup_not_assigned_yes_merely_by_harmonious_aspect():
    q='Расстанутся ли моя подруга Вика и её муж Александр?'
    r=calculate({**BASE,'question':q})
    assert r['question_kind']=='yesno'
    assert 'расставан' in (r['simple_answer']['label']+r['simple_answer']['summary']).lower() or 'разрыв' in r['simple_answer']['label'].lower()
    assert r['simple_answer']['label']!='Скорее да'


def test_explicit_call_has_question_facing_answer():
    q='Позвонит ли мне бывший муж в течение двух недель?'
    r=calculate({**BASE,'question':q})
    assert 'звон' in r['simple_answer']['label'].lower()
    assert r['horizon_days']==14


def test_template_contains_manual_fields_and_visibility():
    h=(Path(__file__).parents[1]/'static'/'index.html').read_text()
    for name in ['person-a-description','person-b-link-description','person-b-link-house','person-b-role-description','person-b-role-house','focus-manual-text','focus-manual-house','setManualVisibility']:
        assert name in h
