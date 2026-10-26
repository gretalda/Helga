"""Regression cases from the user: fully worded questions should be parsed without buttons."""
from fastapi.testclient import TestClient
from main import app
from horary import calculate,question_kind
from question_context import infer_context,resolve_two_people

client=TestClient(app)
BASE={'city':'minsk','datetime':'2026-10-26T11:00'}

def test_full_question_friend_and_husband_no_clarification():
    q='Как будут складываться отношения у моей подруги Вики с её мужем Александром?'
    p=infer_context(q)
    assert p['mode']=='two_people' and not p['needs_clarification']
    assert (p['first_role'],p['relation_to_first'])==('friend','spouse')
    r=calculate({**BASE,'question':q})
    assert (r['actor_house'],r['significators']['house'])==(11,5)
    assert r['question_kind']=='direction'
    assert '11-го = 5-й' in r['scope']

def test_full_question_about_my_ex_and_his_girlfriend():
    q='Что происходит между моим бывшим мужем Александром и его девушкой Викой?'
    p=infer_context(q)
    assert (p['first_role'],p['relation_to_first'])==('ex_partner','romance')
    r=calculate({**BASE,'question':q})
    assert (r['actor_house'],r['significators']['house'])==(7,11)
    assert r['question_kind']=='status'

def test_bare_names_prompt_for_relations_not_guess():
    q='Как будут складываться отношения у Вики с Александром?'
    p=infer_context(q)
    assert p['mode']=='two_people' and p['needs_clarification']
    response=client.post('/api/horary',json={**BASE,'question':q})
    assert response.status_code==422
    assert response.json()['detail']['needs_participants'] is True
    response=client.post('/api/horary',json={**BASE,'question':q,'people_context':{'first_name':'Вика','second_name':'Александр','first_role':'friend','relation_to_first':'spouse'}})
    assert response.status_code==200
    assert response.json()['actor_house']==11
    assert response.json()['significators']['house']==5
    assert 'Вика' in response.json()['scope']

def test_independent_relations_to_querent():
    q='Как будут складываться отношения у моей подруги Вики с моим бывшим мужем Александром?'
    r=calculate({**BASE,'question':q})
    assert (r['actor_house'],r['significators']['house'])==(11,7)

def test_initial_name_is_supported():
    assert infer_context('Наташа и Сергей помирятся?')['names']==['Наташа','Сергей']

def test_manual_first_house_for_other():
    q='Наташа и Сергей помирятся?'
    r=calculate({**BASE,'question':q,'people_context':{'first_role':'other','first_house':9,'relation_to_first':'spouse'}})
    assert (r['actor_house'],r['significators']['house'])==(9,3)

def test_api_parse_not_requiring_horary_form():
    q='Расстанутся ли моя подруга Вика и её муж Александр?'
    v=client.post('/api/interpret',json={'question':q})
    assert v.status_code==200
    assert not v.json()['needs_clarification']
    assert v.json()['first_role']=='friend'

def test_single_person_questions_unchanged():
    for q,h in [('Позвонит ли мне бывший муж?',7),('Когда моя дочь вернётся домой?',5),('Повышение зарплаты будет?',2)]:
        assert infer_context(q)['mode']=='single'
        assert calculate({**BASE,'question':q})['significators']['house']==h

def test_plain_question_about_people_does_not_invent_two_participants():
    q='Что будет с моими деньгами?'
    assert infer_context(q)['mode']=='single'

def test_preview_html_has_required_controls():
    from pathlib import Path
    html=(Path(__file__).parents[1]/'static'/'index.html').read_text()
    for term in ['id="people-panel"','id="person-a-role"','id="person-b-link"','/api/interpret','people_context']:
        assert term in html
