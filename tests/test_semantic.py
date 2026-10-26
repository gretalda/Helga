from datetime import datetime
import pytest
from horary import resolve_question, ClarificationRequired, question_kind, time_hint, calculate, light_mediators
from main import app
from httpx import AsyncClient, ASGITransport
import asyncio

BASE={'question':'Позвонит ли мне бывший муж в течение 2 недель?', 'city':'minsk', 'datetime':'2026-10-26T12:00'}

def post(data):
    async def do():
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c:
            return await c.post('/api/horary',json=data)
    return asyncio.run(do())

def test_inference_without_buttons_and_time_from_text():
    r=calculate(BASE)
    assert r['significators']['house']==7
    assert r['horizon_days']==14
    assert r['question_kind']=='yesno'
    assert r['resolution']['method']=='определено по тексту'

def test_no_silent_wrong_house():
    r=post({**BASE,'question':'Позвонит ли мне этот человек?'})
    assert r.status_code==422
    assert r.json()['detail']['needs_clarification']
    r=post({**BASE,'question':'Позвонит ли мне этот человек?','focus_choice':'friend'})
    assert r.status_code==200
    assert r.json()['significators']['house']==11

def test_other_requires_house():
    r=post({**BASE,'focus_choice':'other'})
    assert r.status_code==422
    r=post({**BASE,'focus_choice':'other','target_house':9,'manual_focus_text':'спор с бывшим соседом'})
    assert r.status_code==200
    assert r.json()['significators']['house']==9

def test_derived_house_for_relationship_of_ex_and_new_partner():
    r=calculate({**BASE,'question':'Что происходит в отношениях моего бывшего мужа с его девушкой?'})
    assert r['actor_house']==7
    assert r['significators']['house']==11
    assert r['question_kind']=='status'
    assert r['simple_answer']['label'] in ('Есть признаки взаимодействия сторон','Текущее состояние связи неясно')

def test_timing_and_direction_are_interpreted_not_refused():
    r=calculate({**BASE,'question':'Когда мой муж приедет?'})
    assert r['question_kind']=='timing'
    assert 'дата' in r['simple_answer']['label'].lower() or 'ориентир' in r['simple_answer']['label'].lower()
    r=calculate({**BASE,'question':'К чему идёт ситуация на работе?'})
    assert r['question_kind']=='direction'
    assert 'не поддерживает' not in r['simple_answer']['summary']

def test_relationship_child_action_not_querent():
    r=calculate({**BASE,'question':'Подарит ли бывший муж дочери подарок?'})
    assert r['actor_house']==7
    assert r['significators']['house']==5

def test_time_words():
    assert time_hint('В ближайшие две недели',datetime(2026,10,26),None)[0]==14
    assert time_hint('До конца месяца',datetime(2026,10,26),None)[0]==6

def test_receptions_and_mediators_visible():
    r=calculate(BASE)
    assert isinstance(r['receptions'],list)
    assert 'translation' in r['light_mediators']
    assert 'collection' in r['light_mediators']


def test_html_no_category_buttons_and_clarification_available():
    from pathlib import Path
    html=(Path(__file__).parents[1]/'static'/'index.html').read_text()
    assert 'id="topics"' not in html
    assert 'id="focus_choice"' in html
    assert 'id="r-context"' in html


def test_verbal_genitive_duration_from_question():
    assert time_hint('Позвонит ли он в течение двух недель?',datetime(2026,10,26),None)[0]==14
    assert time_hint('В течение трех месяцев',datetime(2026,10,26),None)[0]==90
    assert time_hint('За пять дней',datetime(2026,10,26),None)[0]==5
