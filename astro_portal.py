# SPDX-License-Identifier: AGPL-3.0-or-later
"""AstroLichno web service: calculated natal, transit, returns and synastry.

Each reading is tied to Swiss Ephemeris (Moshier) values. Editorial text is a
symbolic reading, not a claim that specific events will occur.
"""
from __future__ import annotations
import calendar
import datetime as dt
import math
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import swisseph as swe
from horary import CITIES

VERSION = '1.0.0'
PLANETS = {'Солнце':swe.SUN, 'Луна':swe.MOON, 'Меркурий':swe.MERCURY,
           'Венера':swe.VENUS,'Марс':swe.MARS,'Юпитер':swe.JUPITER,
           'Сатурн':swe.SATURN,'Уран':swe.URANUS,'Нептун':swe.NEPTUNE,'Плутон':swe.PLUTO}
SIGNS=['Овен','Телец','Близнецы','Рак','Лев','Дева','Весы','Скорпион','Стрелец','Козерог','Водолей','Рыбы']
SYMS=['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓']
PLANET_SYMS={'Солнце':'☉','Луна':'☽','Меркурий':'☿','Венера':'♀','Марс':'♂','Юпитер':'♃','Сатурн':'♄','Уран':'♅','Нептун':'♆','Плутон':'♇'}
ANGLES={0:'соединение',60:'секстиль',90:'квадрат',120:'трин',180:'оппозиция'}
DOMAINS={'Солнце':'самовыражение и решения','Луна':'дом, настроение и повседневность',
'Меркурий':'разговоры, документы и планы',
'Венера':'отношения, согласие и удовольствие','Марс':'действия, споры и инициативы',
'Юпитер':'возможности, обучение и расширение планов',
'Сатурн':'обязанности, границы и долгосрочные решения',
'Уран':'обновление привычного порядка','Нептун':'ожидания и неясные обстоятельства',
'Плутон':'глубокие перестройки и контроль'}
HOUSES={1:'личная инициатива',2:'доходы и ресурсы',3:'общение и документы',4:'семья и жильё',5:'романтика и творчество',6:'ежедневные обязанности и здоровье',7:'партнёрство',8:'общие деньги и обязательства',9:'поездки и обучение',10:'работа и статус',11:'друзья и планы',12:'уединение и восстановление'}
SIGNS_LIFE=[
'Начинать важное без долгого ожидания, но оставлять время для завершения.',
'Выбирать устойчивое и проверять, что привычный путь по-прежнему полезен.',
'Узнавать новое и налаживать связи, не распыляясь между идеями.',
'Беречь близкие отношения и отличать свои чувства от фактов.',
'Проявлять себя ярко, не ставя результат в зависимость от чужой оценки.',
'Замечать детали и совершенствовать работу, не стремясь к недостижимому идеалу.',
'Согласовывать желания и границы, не жертвуя своим выбором.',
'Доводить сложные перемены до понятного результата и беречь доверие.',
'Искать новые горизонты и переводить большие планы в реальные шаги.',
'Создавать устойчивую систему и вовремя пересматривать обязательства.',
'Рассматривать нестандартные решения и объяснять свои идеи окружающим.',
'Полагаться на воображение, одновременно проверяя конкретные условия.'
]


def distance(a,b):return abs((a-b+180)%360-180)
def zodiac(x):
    i=int((x%360)//30)
    return {'sign':SIGNS[i],'symbol':SYMS[i],'degree':round(x%30,2),'longitude':round(x%360,5)}
def describe(x):
    z=zodiac(x)
    return f"{z['degree']:05.2f}° {z['sign']}"

def utc_jd(m):
    u=m.astimezone(dt.timezone.utc)
    return swe.julday(u.year,u.month,u.day,u.hour+u.minute/60+(u.second+u.microsecond/1e6)/3600)

def from_jd(j):
    y,m,d,h=swe.revjul(j)
    return dt.datetime(y,m,d,tzinfo=dt.timezone.utc)+dt.timedelta(hours=h)

@lru_cache(maxsize=10000)
def _positions(j):
    return tuple((k,swe.calc_ut(j,v,swe.FLG_MOSEPH|swe.FLG_SPEED)[0][:4]) for k,v in PLANETS.items())
def positions(j):return {k:{'lon':x[0],'lat':x[1],'speed':x[3],'retro':x[3]<0} for k,x in _positions(round(j,8))}

def place_of(profile,prefix=''):
    city=profile.get(prefix+'city','minsk')
    if city!='other':
        if city not in CITIES:raise ValueError('Выберите город из списка или укажите координаты вручную.')
        return {**CITIES[city], 'id':city}
    try:
        lat=float(profile[prefix+'lat']);lon=float(profile[prefix+'lon']);tz=profile[prefix+'tz'].strip()
        ZoneInfo(tz)
    except (KeyError,ValueError,ZoneInfoNotFoundError,TypeError) as exc:
        raise ValueError('Для другого города нужны широта, долгота и пояс вида Europe/Minsk.') from exc
    if not -89.9<=lat<=89.9 or not -180<=lon<=180:raise ValueError('Проверьте широту и долготу. Для домов не используйте полюса.')
    return {'id':'other','name':str(profile.get(prefix+'city_name') or 'Ваш город')[:100],'lat':lat,'lon':lon,'tz':tz}

def birth(profile):
    try:
        date=dt.date.fromisoformat(str(profile.get('birth_date','')))
    except ValueError as exc:raise ValueError('Укажите дату рождения.') from exc
    if date.year<1900 or date.year>2099:raise ValueError('Дата рождения должна быть между 1900 и 2099 годами.')
    known=bool(profile.get('time_known',True))
    time=profile.get('birth_time') if known else '12:00'
    try:
        t=dt.time.fromisoformat(time or '')
    except ValueError as exc:raise ValueError('Укажите время рождения или отметьте «время неизвестно».') from exc
    place=place_of(profile)
    zone=ZoneInfo(place['tz'])
    naive=dt.datetime.combine(date,t)
    options=[naive.replace(tzinfo=zone,fold=i) for i in (0,1)]
    valid=[m for m in options if m.astimezone(dt.timezone.utc).astimezone(zone).replace(tzinfo=None)==naive]
    if not valid:raise ValueError('В указанный час часы переводились. Выберите другое время или уточните данные.')
    if len(valid)==2 and valid[0].utcoffset()!=valid[1].utcoffset():
        if profile.get('birth_fold') not in (0,1):raise ValueError('Повторный час при переводе времени: укажите первое или второе вхождение часа.')
        m=valid[profile['birth_fold']]
    else:m=valid[0]
    return utc_jd(m),place,known


def cusps_at(j,place):
    try:
        cusps,axes=swe.houses_ex(j,place['lat'],place['lon'],b'P')
        return list(cusps),{'ASC':axes[0],'MC':axes[1]}
    except swe.Error:return [],{}

def house_of(lon,cusps):
    if not cusps:return None
    for i,left in enumerate(cusps):
        if (lon-left)%360 < (cusps[(i+1)%12]-left)%360:return i+1
    return 12

def aspects_of(a,b=None,limit=5,identity=False,interchart=False):
    pairs=[];a=list(a.items());b=list(b.items()) if b is not None else a
    for i,(name,x) in enumerate(a):
        for j,(target,y) in enumerate(b):
            if not interchart and j<=i:continue
            if identity and name==target:continue
            d=distance(x['lon'],y['lon'])
            nearest=min(ANGLES,key=lambda ang:abs(d-ang));orb=abs(d-nearest)
            if orb<=limit:
                pairs.append({'a':name,'b':target,'angle':nearest,'aspect':ANGLES[nearest],
                              'orb':round(orb,3),'strength':round(max(0,(limit-orb)/limit),2),
                              'tone':'помогающий' if nearest in (60,120) else 'напряжённый' if nearest in (90,180) else 'усиливающий'})
    return sorted(pairs,key=lambda item:item['orb'])

def chart(profile):
    j,place,known=birth(profile)
    pp=positions(j)
    if not known:pp.pop('Луна',None)
    cusps,axes=cusps_at(j,place) if known else ([],{})
    planets={name:{**zodiac(p['lon']),'retro':p['retro'],'house':house_of(p['lon'],cusps),
                   'speed':round(p['speed'],4)} for name,p in pp.items()}
    return {'jd':j,'place':place,'time_known':known,'planets':planets,
            'raw':pp,'cusps':[round(x,5) for x in cusps], 'angles':{k:round(v,5) for k,v in axes.items()},
            'aspects':aspects_of(pp,limit=5.5), 'limitations':([] if known else ['Время рождения неизвестно: используется условное 12:00, Луна и дома исключены. Планеты вблизи границ знака требуют уточнения времени.'])}

def public_chart(c):
    return {k:c[k] for k in ('place','time_known','planets','cusps','angles','aspects','limitations')}

def pretty_event(a,target,date=None):
    topic_a=DOMAINS.get(a['a'],a['a']);topic_b=DOMAINS.get(a['b'],a['b'])
    if a['angle'] in (60,120):
        interpretation=f"Темы «{topic_a}» и «{topic_b}» могут поддерживать друг друга. Удобнее закреплять результат конкретной договорённостью."
    elif a['angle'] in (90,180):
        interpretation=f"Между темами «{topic_a}» и «{topic_b}» возможны разные требования. Лучше проверить сроки, ресурсы и ожидания, прежде чем делать вывод."
    else:
        interpretation=f"Темы «{topic_a}» и «{topic_b}» могут стать заметнее одновременно. Это акцент, но не обещание конкретного события."
    return interpretation

def natal(profile):
    c=chart(profile);p=c['planets'];sun=p['Солнце'];moon=p.get('Луна')
    houses=c['cusps'];a=c['aspects'][:7]
    intro=f"Солнце в знаке {sun['sign']} показывает центральную тему самовыражения: {SIGNS_LIFE[SIGNS.index(sun['sign'])]}"
    if moon:intro+=f" Луна в знаке {moon['sign']} добавляет собственный эмоциональный ритм и привычные способы восстанавливаться."
    if c['angles']:intro+=f" Асцендент в знаке {zodiac(c['angles']['ASC'])['sign']} описывает первый способ включаться в новые обстоятельства."
    mercury=p['Меркурий'];venus=p['Венера'];mars=p['Марс'];saturn=p['Сатурн'];jupiter=p['Юпитер']
    sections=[
      {'title':'Характер и сильные стороны','body':intro},
      {'title':'Отношения','body':f"Венера в знаке {venus['sign']} символически описывает способ создавать близость, а Марс в знаке {mars['sign']} — проявлять инициативу. Это сочетание стоит рассматривать вместе с аспектами между планетами и положением VII дома, а не по одному знаку."},
      {'title':'Работа и реализация','body':f"Меркурий в знаке {mercury['sign']} связан с мышлением и обсуждением задач. Сатурн в знаке {saturn['sign']} показывает тему дисциплины и ограничений. "+(f"Куспид X дома в знаке {zodiac(houses[9])['sign']} добавляет карьерный контекст." if houses else 'Без точного времени рождения тему X дома определить нельзя.')},
      {'title':'Деньги и ресурсы','body':f"Юпитер в знаке {jupiter['sign']} символизирует способы расширять возможности. "+(f"II дом начинается в знаке {zodiac(houses[1])['sign']}; вопросы бюджета и собственных ресурсов читаются также по его управителю." if houses else 'Для II дома необходимо уточнить время рождения.')},
    ]
    if a:sections.append({'title':'Заметные связи карты','body':' '.join(f"{x['a']} и {x['b']} — {x['aspect']} (орбис {x['orb']}°). {pretty_event(x,p)}" for x in a[:3])})
    return {'type':'natal','title':'Твоя натальная карта','lead':intro,'sections':sections,
            'chart':public_chart(c),'highlights':[{'label':k,'value':describe(c['raw'][k]['lon'])} for k in ('Солнце','Луна','Венера','Марс') if k in c['raw']],
            'note':'Натальная трактовка — символическая интерпретация. Не описание доказанных черт характера или судьбы.'}


def transit_hits(c,j,orb=1.3):
    pp=positions(j)
    fixed={k:{'lon':v['lon']} for k,v in c['raw'].items()}
    hits=aspects_of(pp,fixed,limit=orb,interchart=True)
    for hit in hits:
        hit['natal_house']=house_of(pp[hit['a']]['lon'],c['cusps'])
        hit['transit_lon']=round(pp[hit['a']]['lon'],5)
    return hits

def date_at(d,zone,hour=12):
    return dt.datetime.combine(d,dt.time(hour),ZoneInfo(zone))

def _transit_window(c,date,zone,days=20):
    # Daily midday samples: windows and peak are approximate (exact crossing not asserted).
    data={}
    for i in range(-min(days,60),min(days,60)+1):
        day=date+dt.timedelta(days=i)
        if not 1900<=day.year<=2099:continue
        samples=transit_hits(c,utc_jd(date_at(day,zone)),1.2)
        for a in samples:
            key=(a['a'],a['b'],a['angle'])
            data.setdefault(key,[]).append((day,a['orb'],a['natal_house']))
    windows=[]
    for key,entries in data.items():
        entries.sort();groups=[];group=[]
        for e in entries:
            if group and (e[0]-group[-1][0]).days>1:groups.append(group);group=[]
            group.append(e)
        if group:groups.append(group)
        for run in groups:
            best=min(run,key=lambda p:p[1]);a,b,angle=key
            windows.append({'a':a,'b':b,'angle':angle,'aspect':ANGLES[angle], 'orb':round(best[1],3),
                            'start':run[0][0].isoformat(),'end':run[-1][0].isoformat(),
                            'peak_day':best[0].isoformat(), 'house':best[2],
                            'active':run[0][0]<=date<=run[-1][0]})
    windows.sort(key=lambda w:(not w['active'], abs((date-dt.date.fromisoformat(w['peak_day'])).days), w['orb']))
    return windows

def transit(profile,day,mode='transit'):
    c=chart(profile);place=place_of(profile)
    d=dt.date.fromisoformat(day)
    if not 1900<=d.year<=2099:raise ValueError('Дата прогноза должна быть между 1900 и 2099 годами.')
    j=utc_jd(date_at(d,place['tz']))
    pp=positions(j)
    focus=transit_hits(c,j,2.0)
    if mode=='day':
        focus=[a for a in focus if a['a'] in ('Луна','Солнце','Меркурий','Венера','Марс')][:7]
        if not focus:focus=transit_hits(c,j,3.0)[:4]
    else:focus=focus[:12]
    windows=_transit_window(c,d,place['tz'],10 if mode=='day' else 24)[:16]
    chosen=focus[:5]
    sections=[]
    for a in chosen:
        area=(' Вопросы '+HOUSES[a['natal_house']]+' могут выйти на передний план.' if a.get('natal_house') else '')
        sections.append({'title':f"{a['a']} — {a['aspect']} к натальному {a['b']}",
                         'body':pretty_event(a,c['raw'])+area,
                         'detail':f"Орбис {a['orb']}°. Положение транзитной планеты относится к полудню выбранной даты."})
    if not sections:sections=[{'title':'Фон даты','body':'В выбранный полдень близких мажорных аспектов в орбисе 2° к натальным планетам не найдено. Это не означает отсутствия событий: напряжение или поддержку нельзя вывести только из такого списка.'}]
    title='Твой день' if mode=='day' else 'Транзиты на дату'
    lead=f"На {d.strftime('%d.%m.%Y')} выделены рассчитанные связи между транзитными и натальными планетами. Важно различать кратковременные влияния и более долгий фон."
    return {'type':mode,'title':title,'lead':lead,'sections':sections,'chart':public_chart(c),
            'overlay':{k:round(v['lon'],5) for k,v in pp.items()},'windows':windows,
            'highlights':[{'label':'Дата','value':d.strftime('%d.%m.%Y')},{'label':'Активных аспектов (до 2°)','value':str(len(transit_hits(c,j,2.0)))}],
            'note':'Транзиты рассчитаны на 12:00 местного времени выбранного города. Окна дат получены дневной выборкой: даты пиков ориентировочные, короткие аспекты могли быть пропущены.'}


def return_report(profile,when,body='Солнце',year=None):
    c=chart(profile)
    if body=='Луна' and not c['time_known']:raise ValueError('Для лунара требуется известное время рождения: без него точная натальная Луна не определена.')
    target=c['raw'][body]['lon']
    return_place=place_of(profile,'return_') if profile.get('return_city') else c['place']
    flags=swe.FLG_MOSEPH
    if body=='Солнце':
        if year is None:year=dt.date.fromisoformat(when).year
        year=int(year)
        if not 1900<=year<=2099:raise ValueError('Год соляра должен быть между 1900 и 2099.')
        birthdate=dt.date.fromisoformat(profile['birth_date'])
        day=min(birthdate.day,calendar.monthrange(year,birthdate.month)[1])
        start=dt.datetime.combine(dt.date(year,birthdate.month,day)-dt.timedelta(days=9),dt.time(0),dt.timezone.utc)
        j=swe.solcross_ut(target,utc_jd(start),flags)
        next_j=swe.solcross_ut(target,j+1,flags)
    else:
        date=dt.date.fromisoformat(when)
        localzone=ZoneInfo(return_place['tz'])
        start=dt.datetime.combine(date-dt.timedelta(days=37),dt.time(),dt.timezone.utc)
        j=swe.mooncross_ut(target,utc_jd(start),flags)
        for _ in range(4):
            nxt=swe.mooncross_ut(target,j+0.02,flags)
            if from_jd(nxt).astimezone(localzone).date()>date:break
            j=nxt
        next_j=swe.mooncross_ut(target,j+0.02,flags)
        if from_jd(j).astimezone(localzone).date()>date:raise ValueError('Не удалось определить текущий лунар.')
    if distance(positions(j)[body]['lon'],target)>0.0001:raise ArithmeticError('Точная точка возвращения не подтверждена.')
    p=positions(j);cusp,axes=cusps_at(j,return_place)
    zon=ZoneInfo(return_place['tz']);start_local=from_jd(j).astimezone(zon)
    end_local=from_jd(next_j).astimezone(zon)
    contacts=aspects_of(p,c['raw'],limit=2.5,identity=False,interchart=True)
    contacts=[a for a in contacts if not (a['a']==a['b']==body)][:12]
    lum_house=house_of(p[body]['lon'],cusp)
    natal_body_house=house_of(c['raw'][body]['lon'],c['cusps'])
    headings={1:'личные решения и новый этап',2:'деньги, приобретения и ресурсы',3:'общение, документы и обучение',4:'дом, семья и жильё',5:'творчество, знакомства и дети',6:'здоровье и повседневные обязанности',7:'отношения и договорённости',8:'общие деньги и обязательства',9:'поездки и образование',10:'работа, репутация и цели',11:'друзья, проекты и планы',12:'отдых, переосмысление и закрытые вопросы'}
    label='Соляр' if body=='Солнце' else 'Лунар'
    period=f"{start_local.strftime('%d.%m.%Y %H:%M')} — {end_local.strftime('%d.%m.%Y %H:%M')}"
    sec=[{'title':f'Главная тема {"года" if body=="Солнце" else "месяца"}',
          'body':f"{body} возвращается на свою натальную долготу. "+(f"В этой карте {body.lower()} в {lum_house}-м доме — символический акцент на теме «{headings[lum_house]}»." if lum_house else 'Дома в выбранном месте не удалось рассчитать, поэтому главную сферу по дому назвать нельзя.')},
         {'title':'Отношения и личные планы','body':'В этой карте стоит отдельно изучать Венеру, V и VII дома. ' + (f"Венера находится в {house_of(p['Венера']['lon'],cusp)}-м доме возврата." if cusp else 'Без домов следует ограничиться аспектами Венеры.')},
         {'title':'Работа и финансы','body':'Для этих тем учитываются II, VI и X дома. ' + (f"Юпитер расположен в {house_of(p['Юпитер']['lon'],cusp)}-м доме, Сатурн — в {house_of(p['Сатурн']['lon'],cusp)}-м." if cusp else 'Уточните место возврата для разбора домов.')},
         {'title':'Важные связи с наталом','body':' '.join(f"{a['a']} в карте возврата образует {a['aspect']} к натальному {a['b']} (орбис {a['orb']}°). {pretty_event(a,c['raw'])}" for a in contacts[:4]) if contacts else 'В пределах выбранного орбиса нет близких межкартных мажорных аспектов: это не говорит, что весь период будет пустым.'}]
    if cusp:
        tops=sorted([(sum(house_of(p[n]['lon'],cusp)==h for n in p),h) for h in range(1,13)],reverse=True)[:3]
        sec.append({'title':'В каких сферах сосредоточены планеты','body':' '.join(f"{count} планет в {h}-м доме ({headings[h]})." for count,h in tops if count>=2) or 'Планеты распределены по разным домам; одной явно преобладающей сферы нет.'})
    sec.append({'title':'Как читать этот цикл','body':f"Начало действия карты — точный момент {start_local.strftime('%d.%m.%Y %H:%M')}; следующий возврат — {end_local.strftime('%d.%m.%Y %H:%M')}. Основные сюжеты выбирайте по дому возвращения, акцентным домам и аспектам к наталу. Для проверки конкретных дней сопоставьте этот фон с транзитами."})
    return {'type':'solar' if body=='Солнце' else 'lunar','title':label+' · '+('личный год' if body=='Солнце' else 'лунный месяц'),
            'lead':f"Точное возвращение {body.lower()} рассчитано на {start_local.strftime('%d.%m.%Y в %H:%M')} ({return_place['name']}). Действующий цикл: {period}.",
            'sections':sec,'chart':public_chart(c),'overlay':{k:round(v['lon'],5) for k,v in p.items()},
            'return_chart':{'cusps':[round(v,5) for v in cusp],'angles':axes,'planets':{n:{**zodiac(v['lon']),'house':house_of(v['lon'],cusp)} for n,v in p.items()}},
            'contacts':contacts,'highlights':[{'label':'Начало цикла','value':start_local.strftime('%d.%m.%Y %H:%M')}, {'label':'Конец цикла','value':end_local.strftime('%d.%m.%Y %H:%M')},{'label':'Место возврата','value':return_place['name']}],
            'note':'Дома возврата зависят от фактического места пребывания в момент точного возвращения. Цикл символически описывает темы периода, а не гарантирует события. Аспекты возврата сопоставлены с наталом.'}


def compatibility(p1,p2):
    c=chart(p1);other=chart(p2)
    all_hits=aspects_of(c['raw'],other['raw'],limit=4.5,interchart=True)
    contacts=[]
    # Require at least one personal planet in each contact for readable synthesis.
    personals={'Солнце','Луна','Меркурий','Венера','Марс'}
    for a in all_hits:
        if a['a'] in personals or a['b'] in personals:contacts.append(a)
    sec=[]
    for title,keys in [('Притяжение и симпатия',{'Венера','Марс','Луна','Солнце'}),
                       ('Общение и понимание',{'Меркурий','Луна','Солнце'}),
                       ('Стабильность и границы',{'Сатурн','Венера','Солнце'})]:
        matched=[a for a in contacts if a['a'] in keys and a['b'] in keys][:3]
        if matched:
            parts=[]
            for a in matched:
                label='помогающая' if a['angle'] in (60,120) else 'напряжённая' if a['angle'] in (90,180) else 'усиливающая'
                parts.append(f"{a['a']} первого человека и {a['b']} второго: {a['aspect']} (орбис {a['orb']}°). Это {label} связь; {pretty_event(a,c['raw'])}")
            body=' '.join(parts)
        else:body='В выбранном орбисе близких аспектов между основными планетами этой темы нет. Это не означает отсутствия совместимости.'
        sec.append({'title':title,'body':body})
    return {'type':'compatibility','title':'Совместимость двух карт','lead':'Синастрия сопоставляет положения планет двух людей. Она помогает обсудить символические темы общения, но не доказывает чувства или будущую судьбу отношений.',
            'sections':sec,'chart':public_chart(c),'second_chart':public_chart(other),
            'contacts':contacts[:28],'highlights':[{'label':'Межкартных аспектов до 4,5°','value':str(len(all_hits))},{'label':'Важные аспекты','value':str(len(contacts))}],
            'note':'Совместимость не переводится в процент и не предсказывает верность, измену или брак. Без времени рождения дома и Луна могут быть неизвестны.'}

def progressions(profile,day,method='progression'):
    c=chart(profile);d=dt.date.fromisoformat(day)
    zone=ZoneInfo(c['place']['tz']);target=utc_jd(date_at(d,c['place']['tz']))
    age=(target-c['jd'])/365.242190402
    if age<0:raise ValueError('Дата прогноза раньше рождения.')
    if method=='progression':
        j=c['jd']+age
        moving={name:v for name,v in positions(j).items() if name in ('Солнце','Луна','Меркурий','Венера','Марс')}
    else:
        moving={name:{'lon':(v['lon']+age)%360} for name,v in c['raw'].items()}
        for name,lon in c['angles'].items():moving[name]={'lon':(lon+age)%360}
    matches=aspects_of(moving,c['raw'],limit=0.8,identity=False,interchart=True)
    secs=[]
    for a in matches[:5]:
        secs.append({'title':f"{a['a']} — {a['aspect']} к натальному {a['b']}", 'body':pretty_event(a,c['raw'])+' Это долгий символический фон, точный момент должен проверяться отдельно.'})
    if not secs:secs=[{'title':'Фон периода','body':'В узком орбисе 0,8° не найдено мажорных аспектов к натальным планетам. Это не является выводом об отсутствии важных перемен.'}]
    return {'type':method,'title':'Вторичные прогрессии' if method=='progression' else 'Символические дирекции',
            'lead':f"На {d.strftime('%d.%m.%Y')} возраст в методе составляет {age:.2f} года. "+('В прогрессиях каждому году жизни соответствует примерно один день после рождения.' if method=='progression' else 'В дирекциях используется дуга 1° за год.'),
            'sections':secs,'chart':public_chart(c),'overlay':{name:round(x['lon'],5) for name,x in moving.items()},
            'highlights':[{'label':'Возраст','value':f'{age:.1f} года'},{'label':'Близких аспектов','value':str(len(matches))}],
            'note':'Прогрессии и дирекции — символические астрологические методы. Для прогнозного вывода требуется сопоставление с наталом и другими техниками.'}

def period(profile,start,end):
    a=dt.date.fromisoformat(start);b=dt.date.fromisoformat(end)
    if b<a or (b-a).days>93:raise ValueError('Выберите период от 1 до 94 дней.')
    if a.year<1900 or b.year>2099:raise ValueError('Дата вне диапазона.')
    c=chart(profile);zone=c['place']['tz']
    accumulated={}
    for i in range((b-a).days+1):
        date=a+dt.timedelta(days=i)
        hits=transit_hits(c,utc_jd(date_at(date,zone)),1.2)
        for x in hits:
            key=(x['a'],x['b'],x['angle'])
            accumulated.setdefault(key,[]).append((date,x['orb']))
    windows=[]
    for key,rows in accumulated.items():
        rows.sort();groups=[];group=[]
        for x in rows:
            if group and (x[0]-group[-1][0]).days>1:groups.append(group);group=[]
            group.append(x)
        if group:groups.append(group)
        for group in groups:
            peak=min(group,key=lambda v:v[1]);m,n,angle=key
            windows.append({'a':m,'b':n,'aspect':ANGLES[angle],'angle':angle,
                            'start':group[0][0].isoformat(),'end':group[-1][0].isoformat(),'peak_day':peak[0].isoformat(),'orb':round(peak[1],3)})
    windows.sort(key=lambda x:(x['peak_day'],x['orb']))
    picked=sorted(windows,key=lambda x:x['orb'])[:8]
    sections=[{'title':f"{w['peak_day'][8:10]}.{w['peak_day'][5:7]} — {w['a']} {w['aspect']} {w['b']}",
               'body':f"Расчётный интервал {w['start']} — {w['end']}. "+pretty_event(w,c['raw'])}
              for w in picked]
    if not sections:sections=[{'title':'Без ярких пиков','body':'В этом периоде не обнаружено достаточно тесных мажорных транзитных аспектов с указанными орбисами. Это не позволяет утверждать, что событий не будет.'}]
    return {'type':'period','title':'Личный прогноз на период',
            'lead':f"Период с {a.strftime('%d.%m.%Y')} по {b.strftime('%d.%m.%Y')}. По дням рассчитаны близкие транзитные аспекты к натальной карте; ниже отобраны наиболее точные показатели.",
            'sections':sections,'windows':windows[:40], 'chart':public_chart(c),
            'highlights':[{'label':'Дней в периоде','value':str((b-a).days+1)},{'label':'Расчётных окон','value':str(len(windows))}],
            'note':'Аспекты для периода найдены дневной выборкой в 12:00, поэтому краткие влияния могли быть пропущены. Для синтеза соляра, лунара, прогрессий и дирекций используйте соответствующие разделы.'}

def sign_profile(profile):
    c=chart(profile);p=c['planets']['Солнце'];i=SIGNS.index(p['sign'])
    element=('Огонь','Земля','Воздух','Вода')[i%4]
    planet=('Марс','Венера','Меркурий','Луна','Солнце','Меркурий','Венера','Марс','Юпитер','Сатурн','Сатурн','Юпитер')[i]
    days={'Марс':'Вторник','Венера':'Пятница','Меркурий':'Среда','Луна':'Понедельник','Солнце':'Воскресенье','Юпитер':'Четверг','Сатурн':'Суббота'}
    return {'type':'sign','title':'Мой знак · '+p['sign'],
            'lead':SIGNS_LIFE[i],
            'sections':[{'title':'Знак и символы','body':f"{p['symbol']} {p['sign']} · стихия {element}. Традиционный управитель — {planet}, связанный день недели — {days[planet]}. Это символические соответствия, не личный прогноз."},
                        {'title':'Чем отличается личная карта','body':'У людей с одним солнечным знаком могут быть разные Асценденты, Луна, дома и аспекты. Перейдите в натальную карту, чтобы изучить индивидуальные расчёты.'}],
            'chart':public_chart(c),'highlights':[{'label':'Солнечный знак','value':p['sign']},{'label':'Стихия','value':element},{'label':'Управитель','value':planet}],
            'note':'Раздел «Мой знак» носит ознакомительный характер.'}

def astro_facts(day,city):
    d=dt.date.fromisoformat(day)
    place=CITIES.get(city,CITIES['minsk']);j=utc_jd(date_at(d,place['tz']))
    p=positions(j)
    elong=(p['Луна']['lon']-p['Солнце']['lon'])%360
    if elong<45 or elong>=315:phase='Новолуние / тёмная Луна'
    elif elong<135:phase='Растущая Луна'
    elif elong<225:phase='Полнолуние / убывание после полнолуния'
    else:phase='Убывающая Луна'
    return {'day':day,'weekday':['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье'][d.weekday()],
            'moon_sign':zodiac(p['Луна']['lon'])['sign'],'moon_phase':phase,'elongation':round(elong,2),
            'sun_sign':zodiac(p['Солнце']['lon'])['sign']}
