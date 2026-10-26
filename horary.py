"""Educational traditional horary calculation engine.

Swiss Ephemeris / pyswisseph is AGPL-3.0-or-later licensed. Before
publicly deploying or distributing this software, comply with AGPL
obligations or purchase the appropriate Swiss Ephemeris commercial license.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import math
import swisseph as swe

SIGNS = ['Овен','Телец','Близнецы','Рак','Лев','Дева','Весы','Скорпион','Стрелец','Козерог','Водолей','Рыбы']
SIGN_GLYPHS = ['♈','♉','♊','♋','♌','♍','♎','♏','♐','♑','♒','♓']
RULERS = ['Марс','Венера','Меркурий','Луна','Солнце','Меркурий','Венера','Марс','Юпитер','Сатурн','Сатурн','Юпитер']
EXALT = {'Солнце': 'Овен', 'Луна':'Телец','Юпитер':'Рак','Меркурий':'Дева','Сатурн':'Весы','Марс':'Козерог','Венера':'Рыбы'}
PLANET_IDS = {'Солнце':swe.SUN, 'Луна':swe.MOON, 'Меркурий':swe.MERCURY, 'Венера':swe.VENUS,
              'Марс':swe.MARS, 'Юпитер':swe.JUPITER, 'Сатурн':swe.SATURN}
PLANET_GLYPHS = {'Солнце':'☉','Луна':'☽','Меркурий':'☿','Венера':'♀','Марс':'♂','Юпитер':'♃','Сатурн':'♄'}
ASPECTS = {0:('Соединение','☌'),60:('Секстиль','⚹'),90:('Квадрат','□'),120:('Трин','△'),180:('Оппозиция','☍')}
HOUSE_MEANINGS = {1:'Спрашивающий, его действия и положение',2:'Личные деньги и имущество',3:'Сообщения, братья и сёстры, короткие поездки',4:'Дом, недвижимость, отец, исход дела',5:'Дети, романтические увлечения и творчество',6:'Повседневная работа, болезни и подчинённые',7:'Партнёрство, бывшие супруги, оппоненты',8:'Общие деньги, долги и ресурсы другого человека',9:'Дальние поездки, обучение, право и публикации',10:'Карьера, должность, начальство и репутация',11:'Друзья, поддержка и надежды',12:'Тайны, ограничения и скрытые противники'}
TOPICS = {
    'contact': {'label':'Контакт или сообщение', 'house':7, 'description':'Другой человек представлен VII домом. Для родственника, коллеги или начальника выбор дома требует отдельного анализа.'},
    'relationship': {'label':'Отношения двух людей', 'house':7, 'description':'Вы — I дом, другой человек — VII дом. Для вопросов о третьих лицах нужны производные дома.'},
    'work': {'label':'Работа и должность', 'house':10, 'description':'Вы — I дом, работа или должность — X дом. Конкуренты и посредники рассматриваются отдельно.'},
    'money': {'label':'Личные деньги', 'house':2, 'description':'Вы — I дом, ваши деньги — II дом. Алименты, кредиты и чужие деньги требуют уточнения домов.'},
    'property': {'label':'Дом и имущество', 'house':4, 'description':'Вы — I дом, недвижимость — IV дом. Для продажи также важен покупатель (VII дом).'},
    'children': {'label':'Дети', 'house':5, 'description':'Вы — I дом, ваш ребёнок — V дом. Вопросы о поступках другого человека требуют повернутых домов.'},
    'travel': {'label':'Дальняя поездка', 'house':9, 'description':'Вы — I дом, дальняя поездка — IX дом; короткая дорога может относиться к III дому.'},
}
CITIES = {
 'minsk': {'name':'Минск', 'lat':53.9006,'lon':27.5590,'tz':'Europe/Minsk'},
 'berlin': {'name':'Берлин', 'lat':52.5200,'lon':13.4050,'tz':'Europe/Berlin'},
 'moscow': {'name':'Москва', 'lat':55.7558,'lon':37.6173,'tz':'Europe/Moscow'},
 'warsaw': {'name':'Варшава', 'lat':52.2297,'lon':21.0122,'tz':'Europe/Warsaw'},
 'vilnius': {'name':'Вильнюс', 'lat':54.6872,'lon':25.2797,'tz':'Europe/Vilnius'},
 'telaviv': {'name':'Тель-Авив', 'lat':32.0853,'lon':34.7818,'tz':'Asia/Jerusalem'},
 'london': {'name':'Лондон', 'lat':51.5072,'lon':-0.1276,'tz':'Europe/London'},
 'newyork': {'name':'Нью-Йорк', 'lat':40.7128,'lon':-74.0060,'tz':'America/New_York'},
 'brest': {'name':'Брест', 'lat':52.0976,'lon':23.7341,'tz':'Europe/Minsk'},
 'grodno': {'name':'Гродно', 'lat':53.6814,'lon':23.8343,'tz':'Europe/Minsk'},
 'gomel': {'name':'Гомель', 'lat':52.4345,'lon':30.9754,'tz':'Europe/Minsk'},
 'vitebsk': {'name':'Витебск', 'lat':55.1904,'lon':30.2049,'tz':'Europe/Minsk'},
 'mogilev': {'name':'Могилёв', 'lat':53.9007,'lon':30.3314,'tz':'Europe/Minsk'},
 'batyam': {'name':'Бат-Ям', 'lat':32.0171,'lon':34.7514,'tz':'Asia/Jerusalem'},
 'petah': {'name':'Петах-Тиква', 'lat':32.0840,'lon':34.8878,'tz':'Asia/Jerusalem'},
 'jerusalem': {'name':'Иерусалим', 'lat':31.7683,'lon':35.2137,'tz':'Asia/Jerusalem'},
 'paris': {'name':'Париж', 'lat':48.8566,'lon':2.3522,'tz':'Europe/Paris'},
 'tbilisi': {'name':'Тбилиси', 'lat':41.7151,'lon':44.8271,'tz':'Asia/Tbilisi'},
 'istanbul': {'name':'Стамбул', 'lat':41.0082,'lon':28.9784,'tz':'Europe/Istanbul'},
}

def norm_signed(angle):
    return (angle + 180) % 360 - 180

def angular_distance(a, b):
    return abs(norm_signed(a-b))

def sign_index(lon):
    return int((lon%360)//30)

def degrees_text(lon):
    degree = (lon%30)
    d = int(degree)
    minutes = int(round((degree-d)*60))
    if minutes == 60:
        d += 1;minutes=0
    return f'{d:02d}°{minutes:02d}′ {SIGNS[sign_index(lon)]}'

def house_of(lon,cusps):
    for i in range(12):
        arc = (cusps[(i+1)%12] - cusps[i])%360
        position = (lon-cusps[i])%360
        if position < arc:
            return i+1
    return None

def closest_aspect(a, b, speed_a, speed_b, orb_limit=8.0):
    current = angular_distance(a,b)
    degree = min(ASPECTS.keys(), key=lambda t: abs(current-t))
    orb = abs(current-degree)
    if orb > orb_limit:
        return None
    # Numerical change in orb for a short time step, using actual speeds.
    next_sep = angular_distance(a + speed_a * .01, b + speed_b * .01)
    next_orb = abs(next_sep-degree)
    approaching = next_orb < orb - 1e-8
    exact = orb < .015
    return {'name':ASPECTS[degree][0], 'symbol':ASPECTS[degree][1],
            'angle':degree, 'orb':round(orb,2), 'applying':approaching,
            'phase':'точный' if exact else ('сходящийся' if approaching else 'расходящийся')}



def future_perfection(jd, name_a, name_b, initial_positions, limit_days=365):
    """First *astronomical* exact major aspect before either planet leaves its natal sign.

    Re-evaluates real ephemeris positions; not a horary promise about the event.
    No obstruction/translation/light rules inferred from this calculation.
    """
    if name_a == name_b:
        return None
    orig_a = sign_index(initial_positions[name_a]['longitude'])
    orig_b = sign_index(initial_positions[name_b]['longitude'])
    def at(dt):
        a = swe.calc_ut(jd + dt, PLANET_IDS[name_a], swe.FLG_MOSEPH)[0][0] % 360
        b = swe.calc_ut(jd + dt, PLANET_IDS[name_b], swe.FLG_MOSEPH)[0][0] % 360
        return a,b
    targets = [(degree, orientation) for degree in (0,60,90,120,180) for orientation in ((1,) if degree in (0,180) else (1,-1))]
    def errors(a,b):
        return [(degree, abs(norm_signed(a-b-orient*degree)), norm_signed(a-b-orient*degree)) for degree,orient in targets]
    # Moon changes quickly; 1.5h protects against missing its first exact aspect.
    step = 0.0625 if 'Луна' in (name_a,name_b) else 0.25
    prev_a,prev_b = at(0)
    prev_err = errors(prev_a,prev_b)
    t=step
    while t<=limit_days+1e-9:
        a,b=at(t)
        if sign_index(a)!=orig_a or sign_index(b)!=orig_b:
            # End the scan at the first ingress (or sign reversal). Conservative.
            return None
        curr_err=errors(a,b)
        matches=[]
        for i,(degree,orb,e) in enumerate(curr_err):
            old=prev_err[i][2]
            if abs(old)>175 and abs(e)>175: continue  # wrap, not a zero
            if abs(old)<1e-7:
                matches.append((t-step,degree))
            elif old*e<=0 and abs(e-old)<30:
                lo,hi=t-step,t
                e_lo=old
                for _ in range(24):
                    mid=(lo+hi)/2
                    x,y=at(mid)
                    error=errors(x,y)[i][2]
                    if e_lo*error<=0:hi=mid
                    else:lo=mid;e_lo=error
                matches.append(((lo+hi)/2,degree))
        if matches:
            days,angle=min(matches)
            return {'name':ASPECTS[angle][0], 'symbol':ASPECTS[angle][1],
                    'angle':angle,'days':round(days,3),
                    'description':f'Точный аспект через {days:.1f} сут. (астрономический интервал, не срок события).'}
        prev_err=curr_err
        t+=step
    return None


def essential_dignity(planet, zodiac):
    descriptions=[]
    sign=SIGNS[sign_index(zodiac)]
    if RULERS[sign_index(zodiac)]==planet:descriptions.append('в обители')
    if EXALT.get(planet)==sign:descriptions.append('в экзальтации')
    opposite=(sign_index(zodiac)+6)%12
    if RULERS[opposite]==planet:descriptions.append('в изгнании')
    if EXALT.get(planet)==SIGNS[opposite]:descriptions.append('в падении')
    return descriptions or ['без главных эссенциальных достоинств по знаку']

def plain_language_answer(question, topic, horizon, ruler_a, ruler_b, future_main, moon_voc):
    """A cautious, short, question-facing explanation for a non-astrologer.

    Interpret *only* the limited rules this prototype has actually calculated;
    never infer motives, feelings, certainty or a calendar date for events.
    """
    q = question.strip().lower().lstrip('«"')
    open_starts = ('когда ', 'где ', 'кто ', 'кого ', 'кому ', 'с кем ',
                   'почему ', 'зачем ', 'сколько ', 'какой ', 'какая ',
                   'какое ', 'какие ', 'как ', 'что ', 'чем ')
    open_ended = q.startswith(open_starts)
    focus = {
        'contact': 'общении', 'relationship': 'отношениях', 'work': 'работе',
        'money': 'деньгах', 'property': 'недвижимости или имуществе',
        'children': 'детях', 'travel': 'поездке',
    }.get(topic, 'ситуации')
    suffix = (f'в пределах указанного срока ({horizon} дн.)' if horizon is not None
              else 'без определённого срока')
    prep = 'об' if focus.startswith(('о','а','э','и','у','е')) else 'о'
    caution = ('Это предварительная трактовка хорарной карты, а не подтверждённый факт '
               'или гарантия будущего события.')
    if open_ended:
        return {'kind':'unclear', 'label':'Нужна конкретизация вопроса',
            'summary': ('На вопрос, начинающийся с «когда», «почему», «что» или «с кем», '
                        'нельзя честно ответить просто «да» или «нет». ' 
                        'Для точного разбора здесь нужен отдельный сценарий трактовки.'),
            'reasons':['Карта построена, но автоматическая оценка пока предназначена для вопросов с ответом «да/нет».',
                       'Можно уточнить один проверяемый вопрос и, если важно, обозначить срок.'],
            'note':caution}
    if ruler_a == ruler_b:
        return {'kind':'unclear','label':'Пока нельзя ответить однозначно',
            'summary':'Один и тот же показатель описывает обе стороны вопроса. По нему одному нельзя определить исход.',
            'reasons':['Управители двух выбранных домов совпали.',
                       'Для осмысленного ответа нужно дополнительно исследовать Луну, дома и другие связи.'],
            'note':caution}
    if future_main and (horizon is None or future_main['days'] <= horizon):
        aspect=future_main['name'].lower()
        if future_main['angle'] in (0, 60, 120):
            return {'kind':'positive','label':'Скорее да',
                'summary':f'В вопросе об {focus} есть предварительный показатель движения к результату {suffix}. Но уверенно обещать событие по одной связи планет нельзя.',
                'reasons':[f'Планеты, обозначающие вас и предмет вопроса, идут к точному аспекту ({aspect}).',
                           'В этой версии ещё не проверены все обстоятельства, которые могут помешать результату.'],
                'note':caution}
        return {'kind':'mixed','label':'Возможно, но с трудностями',
            'summary':f'В вопросе об {focus} просматривается развитие {suffix}, однако карта указывает на напряжение. Это не равнозначно однозначному «да».',
            'reasons':[f'Между основными планетами ожидается напряжённый аспект ({aspect}).',
                       'Для вывода об успехе нужно проверить рецепции, препятствия и остальные показатели карты.'],
            'note':caution}
    if horizon is not None:
        if future_main:
            why='Связь между главными планетами возникает позже выбранного срока, а не внутри него.'
        else:
            why='В указанный срок расчёт не обнаружил прямого точного аспекта главных планет до выхода из знака.'
        return {'kind':'caution','label':'Скорее нет в указанный срок',
            'summary':f'Для вопроса {prep} {focus} карта пока не показывает ясного прямого подтверждения результата в ближайшие {horizon} дн. Это не окончательный отказ: другие правила хорара здесь ещё не оценены.',
            'reasons':[why,'Отсутствие прямой связи само по себе не доказывает, что событие невозможно.'],
            'note':caution}
    reasons=['До выхода планет из своих знаков не найден прямой точный аспект между главными управителями.',
             'Чтобы судить о возможности события, нужно проверить дополнительные правила хорара.']
    if moon_voc:
        reasons[1]='Луна также не образует новых основных точных аспектов до выхода из знака; требуются дополнительные проверки.'
    return {'kind':'unclear','label':'Пока нет ясного «да»',
        'summary':f'В вопросе об {focus} явного прямого подтверждения результата пока не видно. Без срока и более полного разбора нельзя уверенно сказать «нет».',
        'reasons':reasons,'note':caution}


def calculate(payload):
    question = str(payload.get('question','')).strip()
    if not 5 <= len(question) <= 500:
        raise ValueError('Напишите конкретный вопрос длиной от 5 до 500 символов.')
    horizon=payload.get('horizon_days')
    if horizon is not None:
        try:horizon=int(horizon)
        except (ValueError,TypeError):raise ValueError('Срок вопроса должен быть числом дней.')
        if not 1<=horizon<=365:raise ValueError('Срок вопроса — от 1 до 365 дней.')
    topic = payload.get('topic')
    if topic not in TOPICS:
        raise ValueError('Выберите тему вопроса.')
    city_id = payload.get('city', 'minsk')
    if city_id == 'other':
        try:
            lat = float(payload['lat']); lon=float(payload['lon']); tz_name=str(payload['tz'])
            city_name=str(payload.get('city_name','Другой город')).strip()[:70] or 'Другой город'
        except (ValueError,KeyError,TypeError):
            raise ValueError('Для своего города укажите широту, долготу и часовой пояс.')
    elif city_id in CITIES:
        c=CITIES[city_id];lat=c['lat'];lon=c['lon'];tz_name=c['tz'];city_name=c['name']
    else:
        raise ValueError('Неизвестный город.')
    if not -66 <= lat <= 66:  # safe operating range of Regiomontanus wheel here
        raise ValueError('В этой версии доступна широта от 66° ю.ш. до 66° с.ш.')
    if not -180<=lon<=180:
        raise ValueError('Долгота должна быть в диапазоне −180…180.')
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError,ValueError,TypeError):
        raise ValueError('Укажите часовой пояс IANA, например Europe/Minsk.')
    raw_time=str(payload.get('datetime',''))
    try:
        local_naive=datetime.fromisoformat(raw_time)
        if local_naive.tzinfo is not None: raise ValueError()
        if local_naive.year < 1900 or local_naive.year > 2100: raise ValueError()
    except (ValueError,TypeError):
        raise ValueError('Введите локальные дату и время с 1900 по 2100 год.')
    fold = int(payload.get('fold',0))
    if fold not in (0,1): raise ValueError('Некорректный выбор времени перевода часов.')
    local = local_naive.replace(tzinfo=tz, fold=fold)
    utc = local.astimezone(timezone.utc)
    if utc.astimezone(tz).replace(tzinfo=None) != local_naive:
        raise ValueError('Это местное время не существует из-за перехода на летнее/зимнее время. Выберите другое время.')
    jd=swe.julday(utc.year,utc.month,utc.day,utc.hour+utc.minute/60+utc.second/3600+utc.microsecond/3600000000)
    cusps,ax=swe.houses_ex(jd,lat,lon,b'R')
    planets={}
    for name,pid in PLANET_IDS.items():
        values,flags = swe.calc_ut(jd,pid,swe.FLG_MOSEPH|swe.FLG_SPEED)
        deg,speed = float(values[0]),float(values[3])
        planets[name]={'name':name,'glyph':PLANET_GLYPHS[name], 'longitude':round(deg,6),
            'speed':round(speed,6), 'sign':SIGNS[sign_index(deg)],'degree':degrees_text(deg),
            'house':house_of(deg,cusps), 'retrograde':speed<0}
    chart_cusps=[{'house':i+1,'longitude':round(v,6),'sign':SIGNS[sign_index(v)],'degree':degrees_text(v)} for i,v in enumerate(cusps)]
    ruler_a=RULERS[sign_index(cusps[0])]
    target_house=payload.get('target_house') or TOPICS[topic]['house']
    try:target_house=int(target_house)
    except (TypeError,ValueError):raise ValueError('Укажите дом вопроса от 2 до 12.')
    if not 2<=target_house<=12:raise ValueError('Дом вопроса должен быть от 2 до 12.')
    ruler_b=RULERS[sign_index(cusps[target_house-1])]
    major_aspect=None
    if ruler_a != ruler_b:
        a,b=planets[ruler_a],planets[ruler_b]
        major_aspect=closest_aspect(a['longitude'],b['longitude'],a['speed'],b['speed'])
    moon=planets['Луна']
    moon_aspect=None
    if ruler_b != 'Луна':
        b=planets[ruler_b]
        moon_aspect=closest_aspect(moon['longitude'],b['longitude'],moon['speed'],b['speed'],10.0)
    future_main=future_perfection(jd,ruler_a,ruler_b,planets)
    future_moon=[{'planet':n,**f} for n in planets if n!='Луна' if (f:=future_perfection(jd,'Луна',n,planets,35))]
    future_moon.sort(key=lambda x:x['days'])
    moon_voc=not bool(future_moon)
    # Mutual sign-rulership reception; names may rule two different signs.
    mutual=(RULERS[sign_index(planets[ruler_a]['longitude'])] == ruler_b and
            RULERS[sign_index(planets[ruler_b]['longitude'])] == ruler_a) if ruler_a!=ruler_b else False
    notes=[]
    if cusps[0]%30 < 3:notes.append('Асцендент в первых 3° знака — в традиционном хораре иногда считается признаком раннего вопроса. Это не автоматический запрет на трактовку.')
    if cusps[0]%30 >27:notes.append('Асцендент в последних 3° знака — возможный признак поздней стадии ситуации. Это не автоматический отказ от ответа.')
    if planets['Сатурн']['house']==7:notes.append('Сатурн в VII доме: традиционное предупреждение о сложности суждения, не самостоятельный признак неудачи.')
    if ruler_a==ruler_b: notes.append('Один и тот же управитель отвечает за оба дома. Для окончательного суждения нужны дополнительные показатели.')
    if mutual: notes.append('Есть взаимная рецепция по обители между управителями выбранных домов.')
    if moon_voc: notes.append('По расчёту ближайших точных мажорных аспектов Луна без курса до выхода из знака. Традиции определения Луны без курса различаются.')
    evidence=[]
    grade='neutral'
    verdict='Нет достаточных оснований для однозначного ответа'
    if major_aspect:
        evidence.append(f"Текущее расстояние между управителями I и {target_house} домов: {major_aspect['name'].lower()} (орбис {major_aspect['orb']:.2f}°), аспект {major_aspect['phase']}.")
    else:
        evidence.append('Сейчас нет близкого мажорного аспекта между управителями выбранных домов в орбисе 8°.')
    if future_main and (horizon is None or future_main['days']<=horizon):
        evidence.append(f"До выхода из знака управители достигают точного аспекта {future_main['name'].lower()}: {future_main['description']}")
        if future_main['angle'] in (0,60,120):
            grade='positive';verdict='Есть показатель возможного сближения или развития'
        else:
            grade='caution';verdict='Есть показатель контакта через препятствия'
    elif future_main and horizon is not None:
        evidence.append(f"Точный аспект управителей наступает через {future_main['days']:.1f} суток, позже указанного срока {horizon} суток.")
        verdict='В пределах выбранного срока нет прямой перфекции управителей'
    else:
        evidence.append('До выхода одной из планет из текущего знака точного мажорного аспекта управителей не найдено (предел поиска — 365 суток).')
    if moon_aspect:
        evidence.append(f"Текущий аспект Луны с управителем {target_house} дома: {moon_aspect['name'].lower()}, орбис {moon_aspect['orb']:.2f}°; {moon_aspect['phase']}.")
    if future_moon:
        f=future_moon[0]
        evidence.append(f"Следующий точный мажорный аспект Луны в этом знаке: {f['name'].lower()} с планетой {f['planet']} через {f['days']:.2f} суток.")
    else:
        evidence.append('До выхода из знака у Луны не найдено точных мажорных аспектов с семью традиционными планетами.')
    for role,planet in [('Управитель I дома',ruler_a),(f'Управитель {target_house} дома',ruler_b)]:
        evidence.append(f"{role} ({planet}) в знаке {planets[planet]['sign']}: {', '.join(essential_dignity(planet,planets[planet]['longitude']))}.")
    if mutual:evidence.append('Между сигнификаторами есть взаимная рецепция по обители.')
    evidence.append('Это предварительное традиционное суждение. Не проверены препятствия и запреты, переводы/собирания света, полная рецепция, производные дома и сроки события.')
    all_aspects=[]
    names=list(planets)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            p,q=planets[a],planets[b]
            aspect=closest_aspect(p['longitude'],q['longitude'],p['speed'],q['speed'],8.0 if 'Луна' in (a,b) else 6.0)
            if aspect:
                all_aspects.append({'a':a,'b':b,**aspect})
    all_aspects.sort(key=lambda x:x['orb'])
    return {'question':question,'topic':TOPICS[topic]['label'],'scope':TOPICS[topic]['description']+' Дом предмета: '+str(target_house)+' — '+HOUSE_MEANINGS[target_house]+'.',
      'city':city_name,'local_time':local.isoformat(timespec='minutes'), 'utc_time':utc.isoformat(timespec='minutes'),
      'timezone':tz_name,'latitude':lat,'longitude':lon,'jd':round(jd,7),
      'asc':round(ax[0],6),'mc':round(ax[1],6),'house_system':'Региомонтан',
      'cusps':chart_cusps,'planets':planets,'aspects':all_aspects,
      'significators':{'self':ruler_a,'subject':ruler_b,'house':target_house,
         'self_pos':planets[ruler_a]['degree'],'subject_pos':planets[ruler_b]['degree']},
      'horizon_days':horizon,'main_aspect':major_aspect,'future_main_aspect':future_main,'moon_aspect':moon_aspect, 'moon_void_of_course':moon_voc,'moon_next':future_moon[:3], 'mutual_reception':mutual,
      'warnings':notes,'verdict':verdict,'grade':grade,'evidence':evidence,
      'simple_answer':plain_language_answer(question,topic,horizon,ruler_a,ruler_b,future_main,moon_voc),
      'version':'0.3.0 (тестовая версия)', 'ephemeris':'Swiss Ephemeris / Moshier',
      'disclaimer':'Астрологическая интерпретация носит символический характер и не является доказательством будущих событий или чувств других людей.'}
