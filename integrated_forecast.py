# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cross-method symbolic consultation and retrospective chart-audit.

Calculations are kept independent of the event narrative. Neither convergence
nor historical matches constitute an empirical prediction probability.
"""
from __future__ import annotations
import datetime as dt
from collections import defaultdict
from typing import Any
import astro_portal as a
import forecast_writer as w

CATEGORIES = ('love','work','money','home','communication','wellbeing','opportunity','self')
THEMES = w.THEMES
METHOD_LABELS={'solar':'соляр','lunar':'лунар','progression':'прогрессии',
               'direction':'дирекции','transit':'транзиты'}


def day_value(value):
    try: date=dt.date.fromisoformat(value)
    except (TypeError,ValueError) as exc: raise ValueError('Проверьте формат даты: ГГГГ-ММ-ДД.') from exc
    if not 1900<=date.year<=2099:raise ValueError('Дата должна быть между 1900 и 2099 годами.')
    return date


def method_signals(contacts,c,method,weight):
    """One evidence per method/area; avoid inflating strength by duplicate aspects."""
    by_area={}
    for x in contacts:
        key=w.evidence_theme(x,c,house_of=a.house_of)
        if key not in CATEGORIES:continue
        orb=float(x.get('orb',2.0)); score=weight+max(0,1.2-orb/2)
        candidate={'method':method,'theme':key,'score':round(score,3),
                   'evidence':f"{x['a']} {x['aspect']} натального {x['b']} (орбис {orb:.2f}°)",
                   'aspect':{'a':x['a'],'b':x['b'],'angle':x['angle'],'orb':orb},
                   'phase':x.get('phase')}
        if key not in by_area or score>by_area[key]['score']:by_area[key]=candidate
    return list(by_area.values())


def active_solar(profile,date):
    """Use the return actually in force, not merely return of calendar year."""
    c=a.chart(profile)
    current=a.return_report(profile,date.isoformat(),'Солнце',date.year)
    start=dt.datetime.strptime(current['highlights'][0]['value'],'%d.%m.%Y %H:%M').date()
    if start>date:
        current=a.return_report(profile,date.isoformat(),'Солнце',date.year-1)
    return current


def solar_signals(sol,c):
    out=[]
    lum=sol['return_chart']['planets']['Солнце']['house']
    if lum in w.HOUSE_THEME:
        theme=w.HOUSE_THEME[lum]
        out.append({'method':'solar','theme':theme,'score':2.1,
                    'evidence':f'Солнце соляра в {lum}-м доме: {w.HOUSE_PERSPECTIVE[lum]}',
                    'aspect':None,'phase':None})
    for hit in method_signals(sol['contacts'],c,'solar',1.2):
        # The return's house position is the primary yearly emphasis; a
        # contact is independent supporting detail, not another solar vote.
        if not any(x['theme']==hit['theme'] for x in out):out.append(hit)
    return out


def merge_sources(c,solar,progression,direction,windows,lunar=None):
    sig=solar_signals(solar,c)
    sig+=method_signals(progression.get('contacts',[]),c,'progression',1.75)
    sig+=method_signals(direction.get('contacts',[]),c,'direction',1.75)
    # Period windows have no house, but natal target and house are used.
    sig+=method_signals(windows,c,'transit',1.05)
    if lunar:
        sig+=method_signals(lunar['contacts'],c,'lunar',0.8)
    groups=defaultdict(list)
    for item in sig:groups[item['theme']].append(item)
    result=[]
    for theme,values in groups.items():
        methods={x['method'] for x in values}
        # The lunar is a monthly context, never an independent substitute
        # for a slow method in establishing a cross-method theme.
        has_long=bool(methods&{'progression','direction'})
        year='solar' in methods
        date='transit' in methods
        agreement=len(methods & {'solar','progression','direction','transit'})
        grade=('несколько методов' if agreement>=3 and has_long else
               'два метода' if agreement>=2 else 'один метод')
        ranked=sorted(values,key=lambda x:-x['score'])
        result.append({'theme':theme,'label':THEMES[theme]['name'],
                       'agreement':agreement,'support':grade,'has_long':has_long,
                       'has_solar':year,'has_transit':date,
                       'methods':[METHOD_LABELS[k] for k in ['solar','progression','direction','transit','lunar'] if k in methods],
                       'evidence':ranked,
                       'score':round(sum(x['score'] for x in ranked if x['method']!='lunar')+0.25*('lunar' in methods),2)})
    return sorted(result,key=lambda x:(-x['agreement'],-x['score'],x['theme']))


def thematic_text(item):
    t=THEMES[item['theme']]
    evidence=item['evidence']
    adverse=sum(x.get('aspect',{}).get('angle') in (90,180) for x in evidence if x.get('aspect'))
    benef=sum(x.get('aspect',{}).get('angle') in (60,120) for x in evidence if x.get('aspect'))
    if adverse>benef:scenario=t['hard']
    elif benef>adverse:scenario=t['positive']
    else:scenario='планы и реальные обстоятельства могут потребовать одновременно выбора и согласования деталей'
    desc=(f"В теме «{t['name'].lower()}» {item['support']} выделяют общий сюжет. "
          f"На практике это может проявиться так: {t['manifest']}. "
          f"Главный акцент: {scenario}. ")
    if item['has_solar'] and item['has_long'] and item['has_transit']:
        desc+='Тема присутствует в годовой карте, длительной технике и календарных транзитах: это повод присмотреться к периоду, но не основание обещать событие.'
    elif item['has_long'] and item['has_transit']:
        desc+='Долгий показатель совпадает с транзитным интервалом, но без годового акцента вывод о событии остаётся осторожным.'
    elif item['has_solar'] and not item['has_long']:
        desc+='Годовая карта подчёркивает сферу, но длительная перестройка теми же расчётными критериями не подтверждена.'
    else:
        desc+='Это символический акцент одного или двух методов, не самостоятельное предсказание.'
    return desc


def window_lines(windows,top_areas,natal,limit=8):
    keys=set(top_areas)
    rows=[]
    for hit in windows:
        theme=w.evidence_theme(hit,natal,house_of=a.house_of)
        if theme not in keys:continue
        # Peak dates come from noon samples, not precise perfections.
        rows.append((float(hit['orb']),hit['peak_day'],theme,hit))
    if not rows:
        return [],'В выбранном диапазоне нет близких дневных транзитных окон для основных тем. Не следует назначать дату события.'
    # Prefer the tightest windows, then present them in calendar order.
    # This avoids showing only the start of a long forecast period.
    rows.sort(key=lambda x:(x[0],x[1]))
    picked=sorted(rows[:limit],key=lambda x:x[1])
    chunks=[]
    for _,date,theme,h in picked:
        chunks.append(f"{h['start']} — {h['end']}: {h['a']} {h['aspect']} натального {h['b']} (тема «{THEMES[theme]['name'].lower()}»)")
    return [p[-1] for p in picked],'\n'.join(chunks)+'\nЭто периоды близких аспектов по ежедневной выборке, а не даты гарантированных событий.'


def retrospective(profile,events,checks=None):
    """User-entered dated event/control audit without post-hoc reliability claims."""
    events=events or [];checks=checks or []
    if len(events)>8 or len(checks)>8:raise ValueError('Для одной проверки допускается до 8 событий и 8 контрольных дат.')
    c=a.chart(profile);result=[]
    for role,rows in (('событие',events),('контроль',checks)):
        for item in rows:
            date=day_value(item.get('date'))
            if date<dt.date.fromisoformat(str(profile['birth_date'])):raise ValueError('Дата проверки не может быть раньше рождения.')
            if date>dt.date.today():
                raise ValueError('Для проверки используйте известные прошлые события.')
            key=str(item.get('theme','')).lower().strip()
            if key not in CATEGORIES:raise ValueError('Укажите сферу проверяемого события из предложенных.')
            description=str(item.get('description','')).strip()[:160]
            if role=='событие' and not description:raise ValueError('Добавьте краткое описание события.')
            s=active_solar(profile,date)
            pr=a.progressions(profile,date.isoformat(),'progression')
            dr=a.progressions(profile,date.isoformat(),'direction')
            trans=a.transit_hits(c,a.utc_jd(a.date_at(date,c['place']['tz'])),1.2)
            ev=(solar_signals(s,c)+method_signals(pr.get('contacts',[]),c,'progression',1.75)
                +method_signals(dr.get('contacts',[]),c,'direction',1.75)
                +method_signals(trans,c,'transit',1.05))
            relevant=[x for x in ev if x['theme']==key]
            methods={x['method'] for x in relevant}
            matched=len(methods)
            result.append({'role':role,'date':date.isoformat(),'theme':key,'theme_title':THEMES[key]['name'],
                           'description':description if role=='событие' else 'На эту дату событие по выбранной теме не отмечено',
                           'matched_methods':[METHOD_LABELS[m] for m in ('solar','progression','direction','transit') if m in methods],
                           'method_count':matched,
                           'assessment':('совпадение нескольких методов' if matched>=2 else
                                         'совпадение одного метода' if matched==1 else 'совпадений в выбранных орбисах нет'),
                           'evidence':[x['evidence'] for x in relevant]})
    summary={'events':len(events),'controls':len(checks),
             'event_multiple':sum(x['method_count']>=2 for x in result if x['role']=='событие'),
             'event_missing':sum(x['method_count']==0 for x in result if x['role']=='событие'),
             'control_multiple':sum(x['method_count']>=2 for x in result if x['role']=='контроль'),
             'control_missing':sum(x['method_count']==0 for x in result if x['role']=='контроль')}
    return {'entries':result,'summary':summary,
            'methodology':'Сравниваются заранее выбранные пять мажорных аспектов (0°, 60°, 90°, 120°, 180°); прогрессии и дирекции до 0,8°, транзиты до 1,2° в полдень. Соляр проверяется по дому Солнца и контактам. Контрольные даты нужны, чтобы видеть возможные ложные совпадения. Это тест согласованности метода, а не измерение точности предсказаний. С ZET сравнение производится отдельно.'}


def integrated(profile,start,end,events=None,controls=None):
    start_d=day_value(start);end_d=day_value(end)
    if end_d<start_d or (end_d-start_d).days>93:raise ValueError('Комплексный прогноз: выберите период от 1 до 94 дней.')
    if start_d<dt.date.fromisoformat(str(profile['birth_date'])):raise ValueError('Начало прогноза раньше рождения.')
    natal=a.chart(profile)
    if not natal['time_known'] or not natal['cusps']:
        raise ValueError('Для полноценного синтеза по домам требуется известное точное время рождения и рассчитанные дома. Без них доступны самостоятельные транзиты и натал.')
    sol=active_solar(profile,start_d)
    pr=a.progressions(profile,start,'progression')
    dr=a.progressions(profile,start,'direction')
    trans=a.period(profile,start,end)
    lunar=a.return_report(profile,start,'Луна')
    signals=merge_sources(natal,sol,pr,dr,trans['windows'],lunar)
    leading=signals[:4]
    if leading:
        labels=' и '.join('«'+x['label'].lower()+'»' for x in leading[:2])
        lead=(f'С {start_d:%d.%m.%Y} по {end_d:%d.%m.%Y} наиболее заметные пересечения методов относятся к темам {labels}. '
              f'Это согласование символических техник, а не вероятность событий. '
              f'Наибольшее внимание заслуживают темы, повторяющиеся в нескольких независимых методах.')
    else:lead='В выбранном интервале нет достаточно тесных связей по установленным орбисам, чтобы обосновать ведущую тему или назвать событие.'
    solar_period=f"{sol['highlights'][0]['value']} — {sol['highlights'][1]['value']}"
    sun_house=sol['return_chart']['planets']['Солнце']['house']
    year_text=(f'Действует соляр {solar_period}. Солнце соляра в {sun_house}-м доме: {w.HOUSE_PERSPECTIVE.get(sun_house,"дом не определён")}. '
               'Это сюжет годового цикла, но не обещание конкретного исхода.')
    pr_text=('Вторичные прогрессии: '+('; '.join(x['evidence']+(' — '+x['phase'] if x.get('phase') else '') for x in method_signals(pr.get('contacts',[]),natal,'progression',1.75)[:3])
                if pr.get('contacts') else 'в орбисе 0,8° мажорных аспектов не найдено.'))
    dr_text=('Символические дирекции (1° за год): '+('; '.join(x['evidence']+(' — '+x['phase'] if x.get('phase') else '') for x in method_signals(dr.get('contacts',[]),natal,'direction',1.75)[:3])
                if dr.get('contacts') else 'в орбисе 0,8° мажорных аспектов не найдено.'))
    focus_themes=[x['theme'] for x in leading[:3]]
    dated,dates_text=window_lines(trans['windows'],focus_themes,natal)
    sections=[{'title':'Общий фон и главное','body':lead},
              {'title':'Тема личного года — соляр','body':year_text},
              {'title':'Длительные изменения — прогрессии и дирекции','body':pr_text+'\n\n'+dr_text},
              {'title':'Когда фон может проявляться — транзитные интервалы','body':dates_text}]
    for item in leading:
        sections.append({'title':item['label'],'body':thematic_text(item),
                         'detail':'Основание по методам: '+'; '.join(x['method']+': '+x['evidence'] for x in item['evidence'][:4])})
    for theme in ('love','work','money','home'):
        if theme not in {x['theme'] for x in leading}:
            sections.append({'title':THEMES[theme]['name'],
                             'body':'Этот раздел не оказался среди наиболее сильных пересечений выбранных методов. Из этого нельзя делать вывод, что в реальной жизни здесь не будет изменений.'})
    validation=retrospective(profile,events,controls) if events or controls else None
    if validation:
        s=validation['summary'];sections.append({'title':'Проверка на известных прошлых событиях',
           'body':f"Введено событий: {s['events']}, контрольных дат: {s['controls']}. Несколько методов совпали с темой {s['event_multiple']} событий и {s['control_multiple']} контрольных дат; на {s['event_missing']} событиях совпадений нет. Эти числа не показывают доказательную точность прогноза. Подробности — ниже."})
    else:
        sections.append({'title':'Проверка по прошлым событиям ещё не выполнена',
                         'body':'Для профессиональной проверки внесите реальные известные события и контрольные даты. Следует фиксировать и совпадения, и принципиальные расхождения. Без этих данных метод нельзя считать проверенным по биографии.'})
    return {'type':'integrated','title':'Комплексный персональный прогноз','lead':lead,'sections':sections,
            'chart':a.public_chart(natal),'return_chart':sol['return_chart'],
            'windows':dated,'method_windows':trans['windows'],'validation':validation,
            'themes':signals,'method_report':{
                'solar':{'cycle':solar_period,'return_house':sun_house},
                'lunar':{'cycle':lunar['highlights'][0]['value']+' — '+lunar['highlights'][1]['value']},
                'progression':{'contacts':pr.get('contacts',[])[:15]},
                'direction':{'contacts':dr.get('contacts',[])[:15]}},
            'zet_reference':{'engine':'Swiss Ephemeris / Moshier', 'houses':'Placidus',
                'directions':'1 degree per tropical year, all natal objects shifted together',
                'progressions':'1 day after birth for 1 tropical year of life',
                'natal_positions':{k:round(v['lon'],5) for k,v in natal['raw'].items()},
                'natal_angles':natal['angles'],
                'progressed_positions':pr['overlay'],'directed_positions':dr['overlay'],
                'solar_cycle':solar_period},
            'highlights':[{'label':'Период','value':f'{start_d:%d.%m.%Y} — {end_d:%d.%m.%Y}'},
                          {'label':'Активный соляр','value':solar_period},
                          {'label':'Согласованных сфер','value':str(sum(x['agreement']>=2 for x in signals))}],
            'note':'Проверка выполнена по расчётам Swiss Ephemeris/Moshier с системой домов Плацидуса. Соляр — место на момент возвращения (уточните в анкете), дирекции символические 1°/год, прогрессии день/год, транзиты дневная выборка в 12:00; короткие включения и точные даты могут быть пропущены. Это не сверка с программой ZET и не доказательство события. Отчёт не сохраняет введённые события на сервере.'}