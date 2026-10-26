"""Educational traditional horary calculation engine.

Swiss Ephemeris / pyswisseph is AGPL-3.0-or-later licensed. Before
publicly deploying or distributing this software, comply with AGPL
obligations or purchase the appropriate Swiss Ephemeris commercial license.
"""
from datetime import datetime, timezone, timedelta
import re
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
    'other': {'label':'Другой вопрос', 'house':2,'description':'Дом выбран по смыслу конкретного вопроса, требуется проверка трактовки.'},
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

# Semantic context is intentionally conservative. We never silently assign the
# VII house to an unidentified relative or stranger.
FOCUS_CHOICES = {
 'partner': {'label':'Партнёр / супруг / бывший супруг', 'topic':'relationship','house':7},
 'acquaintance': {'label':'Знакомый или другой человек', 'topic':'contact','house':7},
 'friend': {'label':'Друг / подруга', 'topic':'contact','house':11},
 'coworker': {'label':'Коллега / сотрудник', 'topic':'work','house':6},
 'boss': {'label':'Руководитель', 'topic':'work','house':10},
 'child': {'label':'Мой ребёнок', 'topic':'children','house':5},
 'work': {'label':'Моя работа / должность', 'topic':'work','house':10},
 'money': {'label':'Мои деньги', 'topic':'money','house':2},
 'property': {'label':'Дом / недвижимость', 'topic':'property','house':4},
 'travel': {'label':'Моя поездка', 'topic':'travel','house':9},
 'vehicle': {'label':'Автомобиль / личная вещь', 'topic':'other','house':2},
 'health': {'label':'Здоровье', 'topic':'other','house':6},
 'studies': {'label':'Учёба / экзамены', 'topic':'other','house':9},
 'documents': {'label':'Документы / письма', 'topic':'other','house':3},
 'other': {'label':'Другое (выбрать дом самостоятельно)', 'topic':'other','house':None},
}

class ClarificationRequired(ValueError):
    pass


def question_kind(question):
    q=question.strip().lower().lstrip('«"')
    if re.match(r'^(когда|через сколько|в какой (день|месяц|год|срок))\b',q): return 'timing'
    if re.search(r'^(что (сейчас )?происходит|что между|какие (сейчас )?отношения|как (сейчас )?(идут|складываются|развиваются)|в каком (состоянии|моменте)|что (он|она) чувствует|каково отношение)',q): return 'status'
    if re.search(r'^(к чему|куда (идут|ведут)|чем (закончится|завершится)|как будет развиваться|каково будущее|что будет дальше|как (все|всё) закончится|как долго продлится)',q): return 'direction'
    if re.search(r'^(почему|зачем|кто |где |с кем |кого |какая |какое |какие |как |что |сколько )',q): return 'open'
    return 'yesno'


def resolve_question(question, requested_topic=None, focus_choice=None, manual_house=None):
    q=question.lower().replace('ё','е')
    if focus_choice:
        if focus_choice not in FOCUS_CHOICES: raise ValueError('Неизвестный тип участника вопроса.')
        chosen=FOCUS_CHOICES[focus_choice]
        if focus_choice == 'other' and manual_house is None:
            raise ClarificationRequired('Для темы «Другое» откройте расширенные настройки и выберите дом предмета вопроса.')
        house=manual_house if manual_house is not None else chosen['house']
        return {'topic':chosen['topic'] if chosen['topic'] in TOPICS else 'other', 'house':house,
                'method':'уточнение пользователя', 'label':chosen['label'], 'actor_house':1,
                'caution':'Дом выбран по уточнению пользователя; вопросы о третьих лицах требуют проверки производных домов.'}
    if requested_topic in TOPICS:
        return {'topic':requested_topic,'house':manual_house or TOPICS[requested_topic]['house'],
                'method':'выбор темы (старый API)','label':TOPICS[requested_topic]['label'],'actor_house':1,
                'caution':'Тема была передана явно; для третьих лиц проверьте производные дома.'}
    # The most specific people and derived houses first.
    if re.search(r'бывш\w* (муж|жен)|\b(муж|жен|супруг|супругу|супруга|партнер|любим|бойфренд)\w*',q) and re.search(r'(его|ее|не[её]|у него|у нее|с его|с ее)\s+(девушк|парн|женщин|партнер|любовниц)\w*',q):
        return {'topic':'relationship','house':11,'actor_house':7,'method':'производные дома',
                'label':'Отношения партнёра с его романтическим партнёром',
                'caution':'Проверка: партнёр — VII дом, его романтический интерес — V от VII, то есть XI дом. Для брака и иных связей дома могут отличаться.'}
    # A question about an action between two named roles must not use the
    # querent's I-house as the actor just because the child is mentioned.
    parent_person=re.search(r'\b(муж|жен[аы]|супруг|бывш\w* муж)\w*',q)
    named_child=re.search(r'\b(доч|сын|ребен|дет)\w*',q)
    if parent_person and named_child and re.search(r'\b(позвон|подар|поздрав|увид|встрет|приед|прилет|забер)\w*',q):
        return {'topic':'children','house':5,'actor_house':7,'method':'две стороны вопроса',
                'label':'Действия партнёра по отношению к ребёнку',
                'caution':'Партнёр — VII дом, ребёнок спрашивающего — V дом. При другом родстве или смысле действия выбор домов необходимо проверять.'}
    if parent_person and named_child and re.search(r'его\s+(ребен|дет|доч|сын)',q):
        return {'topic':'children','house':11,'actor_house':7,'method':'производные дома',
                'label':'Ребёнок партнёра (V от VII)',
                'caution':'Ребёнок партнёра — XI дом как V от VII. Точно определить родство по короткому вопросу бывает невозможно.'}
    rules=[
      (r'\b(сын|доч[ькреи]|ребен|ребенк|дет[иея]|малыш)\w*','children',5,'Мой ребёнок'),
      (r'\b(муж|жен|супруг|партнер|любим|бывш|бойфренд|девушк|парень)\w*','relationship',7,'Партнёр / бывший партнёр'),
      (r'\b(начальник|директор|руководител|босс)\w*','work',10,'Руководитель'),
      (r'\b(коллег|сотрудник)\w*','work',6,'Коллега'),
      (r'\b(подруг|друг|приятел)\w*','contact',11,'Друг / подруга'),
      (r'\b(машин|автомобил|авто|ремонт авто|транспортн\w* средст)\w*','other',2,'Автомобиль / личное имущество'),
      (r'\b(документ|письм|уведомлен|сообщен|справк)\w*','other',3,'Документы / сообщение'),
      (r'\b(экзамен|учеб|учеба|диплом|университет|образован)\w*','other',9,'Учёба / экзамен'),
      (r'\b(самочувств|здоров|болезн|выздоров|врач|лечен)\w*','other',6,'Здоровье'),
      (r'\b(зарплат|деньг|доход|прибыл|кредит|финанс|денеж|оплат|алимент)\w*','money',2,'Деньги / доход'),
      (r'\b(работ|должност|карьер|повышен|увол|трудоустро|ваканс|собеседован)\w*','work',10,'Работа / карьера'),
      (r'\b(квартир\w*|дом|доме|дома|недвижимост\w*|жиль\w*|переезд\w*)','property',4,'Дом / недвижимость'),
      (r'\b(поездк|полет|путешеств|самолет|рейс|улеч|вылеч|прилет)\w*','travel',9,'Дальняя поездка'),
    ]
    for pattern,topic,house,label in rules:
        if re.search(pattern,q):
            return {'topic':topic,'house':manual_house or house,'actor_house':1,'method':'определено по тексту',
                    'label':label,'caution':'Автоматическое распознавание может ошибаться. Если речь о другом человеке или производных домах, проверьте выбор.'}
    if manual_house is not None:
        return {'topic':'other','house':manual_house,'actor_house':1,'method':'дом выбран вручную',
                'label':'Другое: дом '+str(manual_house),'caution':'Пользователь выбрал дом вручную. Значение дома зависит от контекста вопроса.'}
    raise ClarificationRequired('Не удалось надёжно определить, о ком или о чём вопрос. Уточните участника в поле ниже — иначе карта может отвечать не на тот вопрос.')


def time_hint(question, local_dt, explicit):
    if explicit is not None:return explicit,'вручную'
    q=question.lower().replace('ё','е')
    words={'одну':1,'один':1,'одна':1,'две':2,'два':2,'три':3,'четыре':4,'пять':5,'шесть':6,'семь':7,'восемь':8,'девять':9,'десять':10,'двух':2,'трех':3,'четырех':4,'пяти':5,'шести':6,'семи':7,'восьми':8,'девяти':9,'десяти':10,'одной':1,'одного':1}
    verbal=re.search(r'(?:\bв\s+(?:(?:ближайш|следующ)\w+\s+|течение\s+)?|\bза\s+)('+ '|'.join(words) + r')\s+(недел\w*|дн\w*|месяц\w*)',q)
    if verbal:
        unit=verbal.group(2);value=words[verbal.group(1)]*(7 if unit.startswith('недел') else 30 if unit.startswith('месяц') else 1)
        if 1<=value<=365:return value,'из текста вопроса (условная длина месяца — 30 дней)'
    patterns=[(r'в течение\s+(\d{1,3})\s*дн',1),
              (r'в (?:ближайш(?:ие|их)|следующ(?:ие|их))\s+(\d{1,3})\s*дн',1),
              (r'в течение\s+(\d{1,2})\s*недел',7),
              (r'в (?:ближайш(?:ие|их)|следующ(?:ие|их))\s+(\d{1,2})\s*недел',7),
              (r'в течение\s+(\d{1,2})\s*месяц',30)]
    for pattern,mul in patterns:
        mt=re.search(pattern,q)
        if mt:
            value=int(mt.group(1))*mul
            if 1<=value<=365:return value,'из текста вопроса (условная длина месяца — 30 дней)'
    if re.search(r'до конца (этой |текущей )?недел',q):
        day=(6-local_dt.weekday())
        return max(1,day+1),'из текста вопроса'
    if re.search(r'до конца (этого |текущего )?месяц',q):
        if local_dt.month==12:next_month=local_dt.replace(year=local_dt.year+1,month=1,day=1)
        else:next_month=local_dt.replace(month=local_dt.month+1,day=1)
        return max(1,(next_month.date()-local_dt.date()).days),'из текста вопроса'
    return None,'срок не задан'


# Traditional dignities: Lilly, Christian Astrology (Ptolemaic terms and
# traditional day/night triplicity rulers). This is an explicit choice of
# table; Egyptian bounds or participating triplicity yield other results.
# Entries are exclusive upper degree limits within each 30-degree sign.
PTOLEMAIC_TERMS = [
 [('Юпитер',6),('Венера',14),('Меркурий',21),('Марс',26),('Сатурн',30)],
 [('Венера',8),('Меркурий',15),('Юпитер',22),('Сатурн',27),('Марс',30)],
 [('Меркурий',7),('Юпитер',14),('Венера',21),('Сатурн',25),('Марс',30)],
 [('Марс',6),('Юпитер',13),('Меркурий',20),('Венера',27),('Сатурн',30)],
 [('Сатурн',6),('Меркурий',13),('Венера',19),('Юпитер',25),('Марс',30)],
 [('Меркурий',7),('Венера',13),('Юпитер',18),('Сатурн',24),('Марс',30)],
 [('Сатурн',6),('Венера',11),('Юпитер',19),('Меркурий',27),('Марс',30)],
 [('Марс',6),('Юпитер',14),('Венера',21),('Меркурий',27),('Сатурн',30)],
 [('Юпитер',8),('Венера',14),('Меркурий',19),('Сатурн',25),('Марс',30)],
 [('Венера',6),('Меркурий',12),('Юпитер',19),('Марс',25),('Сатурн',30)],
 [('Сатурн',6),('Меркурий',12),('Венера',20),('Юпитер',25),('Марс',30)],
 [('Венера',8),('Юпитер',14),('Меркурий',20),('Марс',26),('Сатурн',30)],
]
# Fire, earth, air, water; early modern Lilly convention: Mars rules
# watery triplicity for both day and night.
TRIPLICITY_DAY = ('Солнце','Венера','Сатурн','Марс')
TRIPLICITY_NIGHT = ('Юпитер','Луна','Меркурий','Марс')
# Chaldean order of 36 ten-degree faces, starting with Mars in Aries.
FACE_ORDER = ('Марс','Солнце','Венера','Меркурий','Луна','Сатурн','Юпитер')
RECEPTION_WEIGHT = {'обитель':5,'экзальтация':4,'триплицитет':3,'терм':2,'декан':1}


def dignity_lords(longitude, is_day):
    """All five essential dignities at an exact longitude (traditional Lilly table)."""
    sign=sign_index(longitude)
    deg=float(longitude)%30
    bound=next(ruler for ruler,upper in PTOLEMAIC_TERMS[sign] if deg < upper)
    trip=((sign % 4))
    # Chaldean faces progress by exactly one planet every 10 zodiac degrees.
    face=FACE_ORDER[(sign*3+int(deg//10))%7]
    exalt=next((planet for planet,z in EXALT.items() if z==SIGNS[sign]),None)
    fall=next((planet for planet,z in EXALT.items() if z==SIGNS[(sign+6)%12]),None)
    return {'обитель':RULERS[sign], 'экзальтация':exalt,
            'триплицитет':(TRIPLICITY_DAY if is_day else TRIPLICITY_NIGHT)[trip],
            'терм':bound,'декан':face,
            'изгнание':RULERS[(sign+6)%12], 'падение':fall}


def dignity_profile(planet, longitude, is_day):
    owners=dignity_lords(longitude,is_day)
    own=[type_name for type_name in RECEPTION_WEIGHT if owners[type_name]==planet]
    weaknesses=[x for x in ('изгнание','падение') if owners[x]==planet]
    score=sum(RECEPTION_WEIGHT[x] for x in own)-sum({'изгнание':5,'падение':4}[x] for x in weaknesses)
    return {'planet':planet,'position':degrees_text(longitude),'rulers':owners,
        'strengths':own,'weaknesses':weaknesses,'score':score,
        'state':('имеет выраженные достоинства' if score>=4 else
                 'имеет небольшую опору' if score>0 else
                 'находится в ослабленном положении' if score<0 else
                 'не имеет собственных достоинств в этой точке')}


def full_reception_analysis(actor,subject,planets,is_day):
    """Evaluate all five dignity types in both directions; negatives are not receptions."""
    profiles={p:dignity_profile(p,planets[p]['longitude'],is_day) for p in {actor,subject}}
    if actor==subject:
        return {'sect':'дневная' if is_day else 'ночная','table':'Птолемеевы термы; дневные/ночные триплицитеты Лилли; халдейские деканы',
          'profiles':profiles,'directions':[],'mutual_types':[],'mutual':False,
          'summary':'Обе стороны имеют одного управителя. Взаимную рецепцию между одной и той же планетой не определяют.',
          'caution':'Положение одного управителя недостаточно для оценки исхода; учитывайте Луну, аспекты и контекст вопроса.'}
    directions=[]
    for guest,receiver in [(actor,subject),(subject,actor)]:
        owners=dignity_lords(planets[guest]['longitude'],is_day)
        positive=[x for x in RECEPTION_WEIGHT if owners[x]==receiver]
        negative=[x for x in ('изгнание','падение') if owners[x]==receiver]
        directions.append({'guest':guest,'receiver':receiver,'positive':positive,'negative':negative,
            'strength':sum(RECEPTION_WEIGHT[x] for x in positive),
            'statement':(f'{receiver} принимает {guest} по '+', '.join(positive) if positive else
                         f'У {receiver} нет положительной рецепции {guest} по пяти достоинствам')})
    mutual=(bool(directions[0]['positive']) and bool(directions[1]['positive']))
    mutual_types=list(directions[0]['positive'])+list(directions[1]['positive']) if mutual else []
    if mutual:
        summary=('Есть взаимная рецепция: ' + directions[0]['statement'] + '; ' + directions[1]['statement'] +
                 '. Это символический показатель взаимного принятия, но не гарантия события или чувств.')
    elif any(d['positive'] for d in directions):
        detail='; '.join(x['statement'] for x in directions if x['positive'])
        summary=f'Рецепция односторонняя: {detail}. Встречного принятия по пяти достоинствам не обнаружено.'
    else:
        summary='Положительной рецепции между главными управителями по пяти достоинствам нет.'
    return {'sect':'дневная' if is_day else 'ночная','table':'Птолемеевы термы; дневные/ночные триплицитеты Лилли; халдейские деканы',
            'profiles':profiles,'directions':directions,'mutual_types':mutual_types,'mutual':mutual,
            'summary':summary,
            'caution':'Наличие рецепции не заменяет перфекцию аспекта и не доказывает поведение, намерения или чувства людей.'}



def chart_reception_matrix(planets,is_day):
    """All 7 × 6 directed reception checks, plus mutual pair detection."""
    directed=[]
    for guest in PLANET_IDS:
        owners=dignity_lords(planets[guest]['longitude'],is_day)
        for receiver in PLANET_IDS:
            if guest==receiver:continue
            pos=[t for t in RECEPTION_WEIGHT if owners[t]==receiver]
            neg=[t for t in ('изгнание','падение') if owners[t]==receiver]
            directed.append({'guest':guest,'receiver':receiver,'positive':pos,'negative':neg})
    mutual=[]
    for i,a in enumerate(PLANET_IDS):
        for b in list(PLANET_IDS)[i+1:]:
            ab=next(x for x in directed if x['guest']==a and x['receiver']==b)
            ba=next(x for x in directed if x['guest']==b and x['receiver']==a)
            if ab['positive'] and ba['positive']:
                mutual.append({'a':a,'b':b,'a_received_by_b':ab['positive'], 'b_received_by_a':ba['positive']})
    return {'checks':len(directed), 'directions':directed,
            'positive': [x for x in directed if x['positive']],
            'mutual_pairs':mutual,
            'profiles':{n:dignity_profile(n,p['longitude'],is_day) for n,p in planets.items()},
            'sect':'дневная' if is_day else 'ночная'}


def reception_view(ruler_a,ruler_b,planets,is_day=False):
    """Human-readable compatibility field preserved for existing clients."""
    data=full_reception_analysis(ruler_a,ruler_b,planets,is_day)
    result=[x['statement'] for x in data['directions']]
    for x in data['directions']:
        if x['negative']:
            result.append(f"{x['guest']} в месте {', '.join(x['negative'])} {x['receiver']} (ослабление, не рецепция)")
    return result

def obstruction_candidates(jd, actor, subject, planets, main):
    if not main: return []
    found=[]
    for n in planets:
        if n in (actor,subject):continue
        e1=future_perfection(jd,actor,n,planets,limit_days=min(365,main['days']+1))
        e2=future_perfection(jd,subject,n,planets,limit_days=min(365,main['days']+1))
        for role,event in [('планетой вопроса',e1),('планетой предмета',e2)]:
            if event and event['days']+0.05 < main['days']:
                found.append({'planet':n,'with':role,'days':event['days'], 'aspect':event['name']})
    return sorted(found,key=lambda x:x['days'])[:5]


def light_mediators(jd,actor,subject,planets,main):
    """Candidates only: NOT a full William Lilly judgment."""
    if actor==subject: return {'translation':[], 'collection':[]}
    result={'translation':[],'collection':[]}
    moon=planets['Луна']
    if actor!='Луна' and subject!='Луна':
        for source,destination in [(actor,subject),(subject,actor)]:
            pos=planets[source]
            past=closest_aspect(moon['longitude'],pos['longitude'],moon['speed'],pos['speed'],3)
            future=future_perfection(jd,'Луна',destination,planets,35)
            if past and not past['applying'] and future and future['days'] < 3:
                result['translation'].append({'from':source,'to':destination,'by':'Луна',
                   'prior_separation_orb':past['orb'],'new_aspect':future['name'], 'days':future['days']})
    for mediator in planets:
        if mediator in (actor,subject,'Луна'):continue
        x=future_perfection(jd,mediator,actor,planets,30)
        y=future_perfection(jd,mediator,subject,planets,30)
        if x and y and x['days'] < 30 and y['days'] < 30:
            # Collection requires more checks (speeds, application and dignities).
            result['collection'].append({'by':mediator,'aspect_with_a':x['name'],
                 'aspect_with_b':y['name'],'first_days':min(x['days'],y['days']),
                 'last_days':max(x['days'],y['days'])})
    return result


def situational_answer(kind,question,subject_label,period,future,moon_next,reception,obstructions,moon_voc,actor,subject,planets):
    note='Хорар — символическая астрологическая трактовка, а не способ проверить факты, чужие чувства или точную дату события.'
    next_lunar=(f"Дальше Луна образует {moon_next[0]['name'].lower()} с {moon_next[0]['planet']} (астрономически через {moon_next[0]['days']:.2f} суток)." if moon_next else 'У Луны не найдено следующего точного мажорного аспекта до выхода из знака.')
    obs=f"До сближения управителей видна другая точная связь с {obstructions[0]['planet']}; она может осложнять прямой ход дела, но это не доказанный запрет." if obstructions else 'Явного более раннего вмешательства третьей планеты в этот расчёт не внесено.'
    if kind=='timing':
        if future:
            label='Есть ориентир, но не точная дата'
            summary=(f"Главные показатели сходятся к {future['name'].lower()} примерно через {future['days']:.1f} суток астрономического времени. "
                'Это дата аспекта планет, а НЕ предсказанная дата события. Для хорарного срока дополнительно оценивают положение домов и скорость развития ситуации.')
            reasons=[f"Расстояние до точного аспекта будет пройдено через {future['days']:.1f} суток движения планет.",obs,'Символическая единица времени (день, неделя или месяц) без проверки методики не установлена.']
        else:
            label='Точная дата пока не определяется';summary='Прямого будущего аспекта главных показателей в их текущих знаках не найдено. Называть дату события было бы выдумкой.'
            reasons=['Нужны дополнительные способы определения сроков: Луна, перевод света и проверки препятствий.',next_lunar]
    elif kind=='status':
        a=planets[actor]; b=planets[subject]
        def plain_condition(name,pos):
            dg=essential_dignity(name,pos['longitude'])
            if 'в обители' in dg or 'в экзальтации' in dg:
                state='более устойчивое положение и ресурсы'
            elif 'в изгнании' in dg or 'в падении' in dg:
                state='более сложные обстоятельства, меньше свободы действий'
            else:
                state='смешанные или невыраженные условия'
            if pos['retrograde']:state+=', возможный возврат к прежнему'
            return state
        label='Что показывает карта сейчас'
        summary=(f"По теме «{subject_label}» карта символически описывает положение сторон. "
            f"У первой стороны — {plain_condition(actor,a)}; у второй — {plain_condition(subject,b)}. "
            'Это не проверка реального поведения или чувств людей.')
        reasons=[next_lunar,('Есть будущий точный аспект основных показателей: ситуация может меняться.' if future else 'Прямой связи, ведущей к точному аспекту до смены знака, пока нет.'),obs]
    elif kind=='direction':
        if future:
            label='Тема может получить развитие'
            summary=f"Карта показывает возможное движение ситуации к {future['name'].lower()} между главными показателями. " + ('Для благоприятного исхода ещё нужны дополнительные условия.' if future['angle'] in (90,180) else 'Но даже гармоничный аспект не гарантирует желаемого результата.')
        else:
            label='Ясный итог пока не виден'
            summary='Между главными показателями не обнаружено ближайшего завершённого аспекта до смены знака. По одному этому нельзя объявлять ситуацию законченной.'
        reasons=[next_lunar,obs]
    else:
        label='Нужна более конкретная постановка вопроса';summary='Можно построить карту и описать её показатели, но вопрос не задаёт однозначного события, исхода или сроков.'
        reasons=[next_lunar,'Уточните, какой именно результат хотите проверить, или задайте вопрос «Что происходит?» / «К чему идёт ситуация?».']
    return {'kind':'unclear' if not future else 'mixed', 'label':label,'summary':summary,'reasons':reasons,'note':note}


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


def essential_dignity(planet, zodiac, is_day=False):
    profile=dignity_profile(planet,zodiac,is_day)
    return ([f'в {x}' for x in profile['strengths']] +
            [f'в {x}' for x in profile['weaknesses']]) or ['без собственных эссенциальных достоинств']


def plain_language_answer(question, topic, horizon, ruler_a, ruler_b, future_main, moon_voc, reception_data=None):
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
                           'Рецепции рассчитаны отдельно; также важны препятствия и связи Луны.'],
                'note':caution}
        return {'kind':'mixed','label':'Возможно, но с трудностями',
            'summary':f'В вопросе об {focus} просматривается развитие {suffix}, однако карта указывает на напряжение. Это не равнозначно однозначному «да».',
            'reasons':[f'Между основными планетами ожидается напряжённый аспект ({aspect}).',
                       'Рецепции проверены по пяти достоинствам. Даже при поддержке планет напряжённый аспект требует осторожности.'],
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
             'Дополнительно смотрите рассчитанные рецепции и аспекты Луны; часть правил перфекции ещё требует проверки.']
    if moon_voc:
        reasons[1]='Луна также не образует новых основных точных аспектов до выхода из знака; данные рецепций показаны ниже.'
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
    requested_topic = payload.get('topic')
    focus_choice=payload.get('focus_choice')
    target_house_manual=payload.get('target_house')
    if target_house_manual is not None and str(target_house_manual).strip() != '':
        try:target_house_manual=int(target_house_manual)
        except (TypeError,ValueError):raise ValueError('Выберите дом вопроса от 2 до 12.')
        if not 2<=target_house_manual<=12: raise ValueError('Дом вопроса должен быть от 2 до 12.')
    else:target_house_manual=None
    resolution=resolve_question(question,requested_topic,focus_choice,target_house_manual)
    topic=resolution['topic']
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
    actor_house=resolution['actor_house']
    ruler_a=RULERS[sign_index(cusps[actor_house-1])]
    target_house=resolution['house']
    ruler_b=RULERS[sign_index(cusps[target_house-1])]
    horizon,horizon_source=time_hint(question,local_naive,horizon)
    kind=question_kind(question)
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
    # A traditional chart is diurnal when the Sun is above the horizon.
    # Regiomontanus houses 7 through 12 lie above the horizon.
    is_day=planets['Солнце']['house'] in (7,8,9,10,11,12)
    reception_data=full_reception_analysis(ruler_a,ruler_b,planets,is_day)
    all_receptions=chart_reception_matrix(planets,is_day)
    reception=reception_view(ruler_a,ruler_b,planets,is_day)
    obstruct=obstruction_candidates(jd,ruler_a,ruler_b,planets,future_main)
    mediators=light_mediators(jd,ruler_a,ruler_b,planets,future_main)
    # Mutual sign-rulership reception; names may rule two different signs.
    mutual=reception_data['mutual']
    notes=[]
    if cusps[0]%30 < 3:notes.append('Асцендент в первых 3° знака — в традиционном хораре иногда считается признаком раннего вопроса. Это не автоматический запрет на трактовку.')
    if cusps[0]%30 >27:notes.append('Асцендент в последних 3° знака — возможный признак поздней стадии ситуации. Это не автоматический отказ от ответа.')
    if planets['Сатурн']['house']==7:notes.append('Сатурн в VII доме: традиционное предупреждение о сложности суждения, не самостоятельный признак неудачи.')
    if ruler_a==ruler_b: notes.append('Один и тот же управитель отвечает за оба дома. Для окончательного суждения нужны дополнительные показатели.')
    if obstruct:notes.append('Возможны вмешивающиеся аспекты третьих планет ДО перфекции; это предварительный список, не окончательный запрет (prohibition).')
    if mediators['translation']:notes.append('Есть кандидат на перевод света Луной (не окончательное заключение).')
    if mediators['collection']:notes.append('Есть кандидаты на собирание света (требуют дополнительных проверок).')
    if resolution.get('caution'): notes.append(resolution['caution'])
    if mutual: notes.append('Есть взаимная рецепция по традиционным достоинствам между управителями выбранных домов.')
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
    for role,planet in [(f'Управитель {actor_house} дома',ruler_a),(f'Управитель {target_house} дома',ruler_b)]:
        evidence.append(f"{role} ({planet}) в знаке {planets[planet]['sign']}: {', '.join(essential_dignity(planet,planets[planet]['longitude'],is_day))}.")
    evidence.append('Все пять рецепций проверены ('+reception_data['sect']+' карта): '+reception_data['summary'])
    for rec in reception:evidence.append('Положение: '+rec+'.')
    if mediators['translation']:
        x=mediators['translation'][0]
        evidence.append(f"Возможный перевод света: Луна отделяется от {x['from']} и приближается к {x['to']}; нужно проверить достаточность орбисов и состояния планет.")
    if mediators['collection']:
        x=mediators['collection'][0]
        evidence.append(f"Кандидат на собирание света планетой {x['by']}; наличие двух аспектов ещё не означает состоявшееся собирание.")
    if obstruct:
        c=obstruct[0];evidence.append(f"Возможный дополнительный аспект: {c['planet']} с {c['with']} через {c['days']:.1f} суток (требует ручной оценки вмешательства).")
    evidence.append('Проверены обитель, экзальтация, триплицитет, терм, декан и знаковые ослабления; остальные кандидаты на вмешательство, перевод/собирание света пока не являются окончательным суждением. Надёжность сроков требует отдельной проверки.')
    all_aspects=[]
    names=list(planets)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            p,q=planets[a],planets[b]
            aspect=closest_aspect(p['longitude'],q['longitude'],p['speed'],q['speed'],8.0 if 'Луна' in (a,b) else 6.0)
            if aspect:
                all_aspects.append({'a':a,'b':b,**aspect})
    all_aspects.sort(key=lambda x:x['orb'])
    simple=(plain_language_answer(question,topic,horizon,ruler_a,ruler_b,future_main,moon_voc,reception_data) if kind=='yesno' else
            situational_answer(kind,question,resolution['label'],horizon,future_main,future_moon,reception,obstruct,moon_voc,ruler_a,ruler_b,planets))
    # Give an immediate plain-language reception finding. Never interpret it as
    # factual affection or substitute it for a perfected applying aspect.
    if ruler_a != ruler_b:
        simple['reasons'].append('Рецепции: '+reception_data['summary'])
        if simple['kind']=='positive' and not any(row['positive'] for row in reception_data['directions']):
            simple['kind']='mixed';simple['label']='Есть возможность, но без явной поддержки'
            simple['summary']='Точный аспект между показателями возможен, однако по всем пяти достоинствам положительного взаимного принятия не обнаружено. Результат не гарантирован.'
    # A positive aspect without checking conditions is no more than a possibility.
    if kind=='yesno' and obstruct and simple['kind']=='positive':
        simple['kind']='mixed';simple['label']='Возможно, но есть препятствия'
        simple['summary']='Между главными планетами есть связь, но другие аспекты происходят раньше. Поэтому обещать однозначный исход нельзя.'
        simple['reasons'].append('Найден кандидат на вмешательство в ход основного аспекта; необходима проверка.')
    if kind=='yesno' and not future_main and simple['label'].startswith('Скорее нет'):
        simple['label']='Пока нет ясного подтверждения'
    if kind=='yesno' and (topic=='other') and simple['kind']=='positive':
        simple['label']='Есть обнадёживающий признак, но вывод предварительный'
        simple['summary']='Главные показатели сближаются, но у этого вида вопроса могут быть дополнительные правила, не учтённые автоматически.'

    return {'question':question,'topic':resolution['label'],
      'scope':f"Сфера: {resolution['label']}. {resolution['method']}. Участник: дом {actor_house}; предмет: дом {target_house} — {HOUSE_MEANINGS[target_house]}.", 
      'resolution':resolution,'question_kind':kind,'horizon_source':horizon_source,'actor_house':actor_house,
      'city':city_name,'local_time':local.isoformat(timespec='minutes'), 'utc_time':utc.isoformat(timespec='minutes'),
      'timezone':tz_name,'latitude':lat,'longitude':lon,'jd':round(jd,7),
      'asc':round(ax[0],6),'mc':round(ax[1],6),'house_system':'Региомонтан',
      'cusps':chart_cusps,'planets':planets,'aspects':all_aspects,
      'significators':{'self':ruler_a,'subject':ruler_b,'house':target_house,
         'self_pos':planets[ruler_a]['degree'],'subject_pos':planets[ruler_b]['degree']},
      'horizon_days':horizon,'main_aspect':major_aspect,'future_main_aspect':future_main,'moon_aspect':moon_aspect, 'moon_void_of_course':moon_voc,'moon_next':future_moon[:3], 'mutual_reception':mutual,'receptions':reception,'reception_analysis':reception_data,'all_receptions':all_receptions,'obstruction_candidates':obstruct,'light_mediators':mediators,
      'warnings':notes,'verdict':verdict,'grade':grade,'evidence':evidence,
      'simple_answer':simple,
      'version':'0.5.1 (тестовая версия)', 'ephemeris':'Swiss Ephemeris / Moshier',
      'disclaimer':'Астрологическая интерпретация носит символический характер и не является доказательством будущих событий или чувств других людей.'}
