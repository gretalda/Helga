from pathlib import Path
from fastapi import FastAPI, HTTPException
from typing import Literal
import astro_portal as portal
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from horary import CITIES, TOPICS, HOUSE_MEANINGS, FOCUS_CHOICES, ClarificationRequired, ParticipantContextRequired, calculate

from question_context import infer_context, ROLE_OPTIONS, RELATION_OPTIONS

app=FastAPI(title='АстроЛично — персональная астрология', version='1.1.0')
DIR=Path(__file__).parent
app.mount('/static',StaticFiles(directory=DIR/'static'),name='static')

class HoraryRequest(BaseModel):
    question:str=Field(max_length=500)
    topic:str|None=None
    focus_choice:str|None=None
    manual_focus_text:str|None=None
    datetime:str
    city:str='minsk'
    city_name:str|None=None
    lat:float|None=None
    lon:float|None=None
    tz:str|None=None
    fold:int=0
    target_house:int|None=None
    people_context:dict|None=None
    horizon_days:int|None=None

@app.get('/')
def homepage():
    return FileResponse(DIR/'static'/'portal.html')

@app.get('/service-worker.js', include_in_schema=False)
def pwa_service_worker():
    # Serve from root so the SW may control the whole app, not just /static/.
    return FileResponse(DIR/'static'/'service-worker.js', media_type='application/javascript', headers={'Cache-Control':'no-cache'})

@app.get('/horary')
def horary_page():
    return FileResponse(DIR/'static'/'index.html')

@app.get('/api/config')
def config():
    return {'cities':CITIES,'topics':TOPICS,'houses':HOUSE_MEANINGS,'focus_choices':FOCUS_CHOICES,'role_options':ROLE_OPTIONS,'relation_options':RELATION_OPTIONS}

@app.get('/api/health')
def health():
    return {'ok':True,'version':'1.1.0'}

class AnalyzeRequest(BaseModel):
    question:str=Field(max_length=500)

@app.post('/api/interpret')
def interpret(body:AnalyzeRequest):
    return infer_context(body.question)

@app.post('/api/horary')
def chart(body:HoraryRequest):
    try:
        return calculate(body.model_dump())
    except ParticipantContextRequired as err:
        raise HTTPException(status_code=422, detail={'message':str(err),'needs_participants':True,'detected':err.detected}) from err
    except ClarificationRequired as err:
        raise HTTPException(status_code=422,detail={'message':str(err),'needs_clarification':True}) from err
    except ValueError as err:
        raise HTTPException(status_code=422,detail=str(err)) from err


class AstroRequest(BaseModel):
    mode:Literal['natal','transits','day','period','solar','lunar','compatibility','progression','direction','sign']
    profile:dict
    second_profile:dict|None=None
    date:str|None=None
    end_date:str|None=None
    solar_year:int|None=None

@app.get('/api/astro/config')
def astro_config():
    return {'version':portal.VERSION,'cities':CITIES,'modes':['natal','transits','day','period','solar','lunar','compatibility','progression','direction','sign']}

@app.post('/api/astro/report')
def astro_report(body:AstroRequest):
    try:
        m=body.mode
        if m=='natal':return portal.natal(body.profile)
        if m=='sign':return portal.sign_profile(body.profile)
        if m in ('transits','day'):return portal.transit(body.profile,body.date, 'day' if m=='day' else 'transit')
        if m=='period':return portal.period(body.profile,body.date,body.end_date)
        if m=='solar':return portal.return_report(body.profile,body.date,'Солнце',body.solar_year)
        if m=='lunar':return portal.return_report(body.profile,body.date,'Луна')
        if m=='compatibility':
            if not body.second_profile:raise ValueError('Добавьте дату рождения второго человека.')
            return portal.compatibility(body.profile,body.second_profile)
        if m in ('progression','direction'):return portal.progressions(body.profile,body.date,m)
        raise ValueError('Неизвестный раздел.')
    except (ValueError,KeyError,OverflowError,ArithmeticError) as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.get('/api/astro/facts')
def astro_facts(date:str,city:str='minsk'):
    try:return portal.astro_facts(date,city)
    except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc)) from exc