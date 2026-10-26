"""Conservative context extraction for Russian horary questions.

No LLM or hidden guesses: deterministic relation hints with explicit clarification
when the participant's relationship to the querent is not stated.
"""
import re
from typing import Optional

ROLE_OPTIONS = {
    'partner': {'label': 'Мой супруг / партнёр', 'house': 7},
    'ex_partner': {'label': 'Мой бывший супруг / партнёр', 'house': 7},
    'friend': {'label': 'Мой друг / подруга', 'house': 11},
    'colleague': {'label': 'Мой коллега', 'house': 6},
    'boss': {'label': 'Мой руководитель', 'house': 10},
    'child': {'label': 'Мой ребёнок', 'house': 5},
    'sibling': {'label': 'Мой брат / сестра', 'house': 3},
    'parent': {'label': 'Мой родитель (традиция домов различается)', 'house': 4},
    'acquaintance': {'label': 'Знакомый / посторонний', 'house': 7},
    'other': {'label': 'Иная связь / нужна ручная настройка домов', 'house': None},
}
RELATION_OPTIONS = {
    'spouse': {'label': 'Его / её супруг или постоянный партнёр', 'house': 7},
    'romance': {'label': 'Его / её романтический интерес', 'house': 5},
    'ex_partner': {'label': 'Его / её бывший партнёр', 'house': 7},
    'friend': {'label': 'Его / её друг / подруга', 'house': 11},
    'colleague': {'label': 'Его / её коллега', 'house': 6},
    'boss': {'label': 'Его / её руководитель', 'house': 10},
    'child': {'label': 'Его / её ребёнок', 'house': 5},
    'parent': {'label': 'Его / её родитель (дом требует проверки)', 'house': 4},
    'sibling': {'label': 'Его / её брат / сестра', 'house': 3},
    'other': {'label': 'Другая связь / выбрать дом вручную', 'house': None},
}

# Word stems intentionally narrow: a spouse is not inferred from the word
# «отношения», and a named person without a role has an unknown house.
PATTERNS = [
    ('ex_partner', r'\bбывш\w*\s+(?:муж\w*|жен\w*|супруг\w*|партн[её]р\w*)'),
    ('friend', r'\b(?:подруг\w*|друг\w*|приятел\w*)'),
    ('colleague', r'\b(?:коллег\w*|сотрудник\w*)'),
    ('boss', r'\b(?:начальник\w*|руководител\w*|директор\w*)'),
    ('child', r'\b(?:доч\w*|сын\w*|реб[её]н\w*|дет\w*)'),
    ('sibling', r'\b(?:брат\w*|сестр\w*)'),
    ('parent', r'\b(?:мат[ьиер]\w*|мам\w*|отец|отц\w*|пап\w*)'),
    ('partner', r'\b(?:муж\w*|жен\w*|супруг\w*|партн[её]р\w*)'),
    ('acquaintance', r'\b(?:знаком\w*|приятел\w*)'),
]
# For links from person 1 to person 2, a boyfriend/girlfriend in unformalized
# relationships is treated as V, a spouse as VII. Different traditions exist.
REL_PATTERNS = [
    ('ex_partner', r'\bбывш\w*\s+(?:муж\w*|жен\w*|партн[её]р\w*)'),
    ('spouse', r'\b(?:муж\w*|жен\w*|супруг\w*)'),
    ('romance', r'\b(?:девушк\w*|парн\w*|любовниц\w*|любовник\w*|возлюбленн\w*|мужчин\w*|женщин\w*)'),
    ('friend', r'\b(?:подруг\w*|друг\w*)'),
    ('colleague', r'\b(?:коллег\w*|сотрудник\w*)'),
    ('boss', r'\b(?:начальник\w*|директор\w*)'),
    ('child', r'\b(?:доч\w*|сын\w*|реб[её]н\w*)'),
    ('parent', r'\b(?:мам\w*|отц\w*|пап\w*|мат[ьиер]\w*)'),
    ('sibling', r'\b(?:брат\w*|сестр\w*)'),
]
OWN = r'(?:мо[ейиюя]|моего|моей|моим|мой|моя|мои|сво[ейюя]|своего)'
THEIR = r'(?:е[её]|его|её|их)'
QUESTION_START = {'Как','Когда','Что','Почему','Будут','Будет','Куда','Есть','Вернется','Вернётся','Сможет','Состоится','Расстанутся','Помирятся','Позвонит','Заплатит','Женится','Выйдет','Встретится','Каковы','Какие','Какая','Чем','Сколько','С','У','Между','Про','По','В','К','До','На','Может','Сможет','Продолжатся','Нужно','Стоит'}
NAME_RX = re.compile(r'(?<![\w-])([А-ЯЁ][а-яё]{2,}(?:-[А-ЯЁ][а-яё]{2,})?)(?![\w-])')


def name_key(name):
    # Merge ordinary case forms: Вика/Вики, Александр/Александром.
    return norm(name)[:3 if len(name) <= 5 else 5]

def names_in_question(text):
    """Ordered named references; case inflections are preserved to display as given."""
    result = []
    for m in NAME_RX.finditer(text):
        name = m.group(1)
        if name in QUESTION_START:
            continue
        if not any(name_key(old)==name_key(name) for old in result):
            result.append(name)
    return result[:3]


def norm(s):
    return str(s or '').lower().replace('ё', 'е').strip()


def role_from_span(span, possessive=OWN, patterns=PATTERNS):
    # A role is inferred only when attached to a clear possessive:
    # «моя подруга», «моего бывшего мужа», «её супруг».
    for code, expression in patterns:
        if re.search(r'\b'+possessive+r'\s+(?:\S+\s+){0,2}(?:'+expression+r')', norm(span)):
            return code
    return None


def associated_role(question, name, possessive=OWN, patterns=PATTERNS):
    # Examine every mention of a name, including appositions such as
    # «Вика — моя подруга» after the actual question.
    for m in NAME_RX.finditer(question):
        if name_key(m.group(1)) != name_key(name):
            continue
        prefix = question[max(0, m.start()-85):m.start()]
        prefix = re.split(r'[,;.!?]|\s+и\s+|\s+с\s+|\s+между\s+|\s+а\s+', prefix)[-1]
        suffix = question[m.end():m.end()+80]
        for portion in (prefix, re.split(r'[,;.!?]|\s+и\s+|\s+с\s+', suffix)[0]):
            val=role_from_span(portion, possessive, patterns)
            if val:return val
    return None


def infer_context(question):
    names = names_in_question(question)
    raw = norm(question)
    # Two separately named people are always about two participants (never
    # silently misread them as querent vs partner).
    has_two_named = len(names)>=2
    third_party_pair = bool(re.search(r'\b(?:бывш\w*\s+)?(?:муж\w*|жен\w*|партн[её]р\w*|подруг\w*)\b.{0,65}\b'+THEIR+r'\s+(?:муж\w*|жен\w*|девушк\w*|парн\w*)',raw))
    third_party_pair |= bool(re.search(r'\b'+OWN+r'\s+(?:подруг\w*|друг\w*).{0,60}\b'+THEIR+r'\s+(?:муж\w*|жен\w*|парн\w*|девушк\w*)',raw))
    if not (has_two_named or third_party_pair):
        return {'mode':'single', 'names': names, 'needs_clarification':False, 'reason':'Нет явной пары участников'}
    first=names[0] if names else 'Первый человек'
    second=names[1] if len(names)>1 else 'Второй человек'
    first_role=associated_role(question,first)
    second_role=associated_role(question,second)
    relation=associated_role(question,second,THEIR,REL_PATTERNS)
    # Unnamed pair: one explicit relational person with their boyfriend/spouse.
    if not names and third_party_pair:
        first_role=role_from_span(raw,OWN,PATTERNS)
        relation=role_from_span(raw,THEIR,REL_PATTERNS)
    # In «мой бывший муж Александр и его девушка Вика» both clues are
    # independently collected; do not let «моего» bind Vika herself.
    complete=bool(first_role and (relation or second_role))
    missing=[]
    if not first_role: missing.append('first_role')
    if not (relation or second_role):missing.append('second_link')
    return {'mode':'two_people','names':names,'first_name':first,'second_name':second,
            'first_role':first_role,'second_role':second_role,'relation_to_first':relation,
            'needs_clarification':not complete,'missing':missing,
            'reason':'Связи определены по тексту' if complete else 'Не хватает сведений о связях участников с вопрошающим'}


def user_description(provided, key, label):
    value = str(provided.get(key) or '').strip()
    if not 3 <= len(value) <= 120:
        raise ValueError(f'Для варианта «Вручную» заполните поле «{label}» (от 3 до 120 символов).')
    return value


def selected_house(provided, key, label):
    try:
        val = int(provided.get(key))
    except (TypeError, ValueError):
        raise ValueError(f'Для варианта «Вручную» выберите {label}.') from None
    if not 1 <= val <= 12:
        raise ValueError(f'Для варианта «Вручную» выберите {label} от I до XII.')
    return val


def resolve_two_people(question, provided=None, manual_house=None):
    detected=infer_context(question)
    if detected['mode'] != 'two_people':
        return None
    provided=provided or {}
    # Explicit user selections override automatic detection, but a blank value
    # does not override a detected role.
    name_first=str(provided.get('first_name') or detected['first_name']).strip()[:80]
    name_second=str(provided.get('second_name') or detected['second_name']).strip()[:80]
    first=provided.get('first_role') or detected['first_role']
    second=provided.get('second_role') or detected['second_role']
    relation=provided.get('relation_to_first') or detected['relation_to_first']
    if first not in ROLE_OPTIONS:
        raise ValueError('Уточните, кто первый человек для вас.')
    if relation and relation not in RELATION_OPTIONS:
        raise ValueError('Неизвестная связь между участниками.')
    if second and second not in ROLE_OPTIONS:
        raise ValueError('Неизвестная связь второго человека с вами.')

    # Manual relations always carry both a readable description and an explicit
    # house choice; never invent a house from an unknown kinship.
    first_label = ROLE_OPTIONS[first]['label']
    if first == 'other':
        first_label=user_description(provided,'first_role_text','Кто первый человек для вас?')
        h1=selected_house(provided,'first_house','дом первого человека')
    else:
        h1=ROLE_OPTIONS[first]['house']

    if relation == 'other':
        rel_label=user_description(provided,'relation_text','Кем второй человек является первому?')
        derivative=selected_house(provided,'relation_house','дом второго человека от первого')
        h2=((h1-1+derivative-1)%12)+1
        mode=f'производный: {derivative}-й от {h1}-го (вручную)'
        second_label=rel_label
        explain_second=f'{name_second}: {derivative}-й дом от {h1}-го = {h2}-й дом ({rel_label}, ручной выбор).'
    elif relation and RELATION_OPTIONS[relation]['house']:
        derivative=RELATION_OPTIONS[relation]['house']
        h2=((h1-1+derivative-1)%12)+1
        mode=f'производный: {derivative}-й от {h1}-го'
        second_label=RELATION_OPTIONS[relation]['label']
        explain_second=f'{name_second}: {derivative}-й дом от {h1}-го = {h2}-й дом.'
    elif second == 'other':
        second_label=user_description(provided,'second_role_text','Кто второй человек для вас?')
        h2=selected_house(provided,'second_house','дом второго человека')
        mode='непосредственно от I дома (вручную)'
        explain_second=f'{name_second}: {h2}-й дом ({second_label}, ручной выбор).'
    elif second and ROLE_OPTIONS[second]['house']:
        h2=ROLE_OPTIONS[second]['house']
        mode='непосредственно от I дома'
        second_label=ROLE_OPTIONS[second]['label']
        explain_second=f'{name_second}: {h2}-й дом ({second_label}).'
    elif manual_house:
        h2=manual_house
        mode='вручную'
        second_label='дом предмета вопроса'
        explain_second=f'{name_second}: {h2}-й дом (вручную).'
    else:
        raise ValueError('Укажите, кем второй человек является первому, либо кем он приходится лично вам.')
    label=f'{name_first} ({first_label}) и {name_second} ({second_label})'
    effective_source=(not provided or not any(str(provided.get(k) or '') and str(provided.get(k)) != str(detected.get(k) or '') for k in ('first_role','second_role','relation_to_first','first_name','second_name')))
    if h1==h2:
        caution='Обе стороны попали в один дом. Для независимого суждения могут понадобиться дополнительные сигнификаторы и уточнение отношений.'
    else:
        caution='Производные дома зависят от смысла вопроса и выбранной традиции; при неоднозначном родстве следует сверить дом. Это не доказательство чужих чувств.'
    return {'topic':'relationship','house':h2,'actor_house':h1,'method':'автоматически по тексту' if effective_source else 'участники уточнены пользователем',
            'label':label,'caution':caution,
            'participants':{'first':name_first,'second':name_second,'first_role':first,'second_role':second,'relation_to_first':relation},
            'house_explanation':f'{name_first}: {h1}-й дом ({first_label}). {explain_second}'}
