from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from horary import CITIES, TOPICS, HOUSE_MEANINGS, FOCUS_CHOICES, ClarificationRequired, calculate

app=FastAPI(title='АстроЛично — Хорар', version='0.5.1')
DIR=Path(__file__).parent
app.mount('/static',StaticFiles(directory=DIR/'static'),name='static')

class HoraryRequest(BaseModel):
    question:str=Field(max_length=500)
    topic:str|None=None
    focus_choice:str|None=None
    datetime:str
    city:str='minsk'
    city_name:str|None=None
    lat:float|None=None
    lon:float|None=None
    tz:str|None=None
    fold:int=0
    target_house:int|None=None
    horizon_days:int|None=None

@app.get('/')
def homepage():
    return FileResponse(DIR/'static'/'index.html')

@app.get('/api/config')
def config():
    return {'cities':CITIES,'topics':TOPICS,'houses':HOUSE_MEANINGS,'focus_choices':FOCUS_CHOICES}

@app.get('/api/health')
def health():
    return {'ok':True,'version':'0.5.1'}

@app.post('/api/horary')
def chart(body:HoraryRequest):
    try:
        return calculate(body.model_dump())
    except ClarificationRequired as err:
        raise HTTPException(status_code=422,detail={'message':str(err),'needs_clarification':True}) from err
    except ValueError as err:
        raise HTTPException(status_code=422,detail=str(err)) from err
