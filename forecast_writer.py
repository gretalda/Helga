# SPDX-License-Identifier: AGPL-3.0-or-later
"""Consultation-style, evidence-bound interpretations for the AstroLichno PWA.

No AI or random prose. Every prioritised theme is grounded in a calculated
aspect, house placement, or cycle. An absent aspect is never called an event.
"""
from __future__ import annotations
import datetime as dt
from collections import Counter

THEMES={
 'self':{'name':'Личные решения и направление жизни',
     'positive':'проще назвать собственную цель, выбрать направление и договориться о следующем шаге',
     'hard':'придётся определять приоритеты, не пытаясь одновременно угодить всем',
     'manifest':'решение, от которого зависит распорядок ближайших месяцев, или желание сменить способ действий'},
 'love':{'name':'Отношения и личная жизнь',
     'positive':'проще обсудить формат общения, предложить встречу или уточнить взаимные ожидания',
     'hard':'разница ожиданий, занятость или принципиальный разговор способны усложнить договорённость',
     'manifest':'инициатива в общении, разговор о границах или попытка согласовать совместные планы'},
 'work':{'name':'Работа, обязанности и статус',
     'positive':'удобнее закрепить договорённость, завершить рабочий этап или представить результат',
     'hard':'понадобятся корректировки сроков, задач и зоны ответственности',
     'manifest':'перераспределение задач, обсуждение условий работы или решение по долгому проекту'},
 'money':{'name':'Финансы и личные ресурсы',
     'positive':'есть повод привести бюджет в порядок, обсудить расчёты или подобрать более удобные условия',
     'hard':'потребуется внимательнее согласовывать траты, обязательства и реальные возможности',
     'manifest':'пересмотр расходов, платежей, накоплений или условий совместного бюджета'},
 'home':{'name':'Дом и семья',
     'positive':'проще обсудить домашние планы, семейные договорённости и распределение забот',
     'hard':'привычный уклад может потребовать перестройки или большей определённости между близкими',
     'manifest':'домашняя организация, вопросы жилья или разговоры о семейных обязательствах'},
 'communication':{'name':'Общение, документы и обучение',
     'positive':'проще прояснить детали разговора, письма, поездки или учебного плана',
     'hard':'в переписке и документах особенно важны сроки и точность формулировок',
     'manifest':'переговоры, оформление бумаг, обучение либо необходимость получить ответ'},
 'wellbeing':{'name':'Повседневный ритм и восстановление',
     'positive':'есть возможность распределить нагрузки и дать себе удобный рабочий темп',
     'hard':'перегрузка делами может потребовать пересмотра графика и отдыха',
     'manifest':'изменение распорядка, перераспределение дел и времени на отдых'},
 'opportunity':{'name':'Новые планы, круг общения и возможности',
     'positive':'можно обсудить перспективную идею, совместный проект или обучение',
     'hard':'новая возможность потребует отбора и проверки её реальной стоимости',
     'manifest':'предложение, обучение, разговор о будущем или изменение круга общения'},
}
HOUSE_THEME={1:'self',2:'money',3:'communication',4:'home',5:'love',6:'wellbeing',7:'love',8:'money',9:'communication',10:'work',11:'opportunity',12:'wellbeing'}
PLANET_THEME={'Солнце':'self','Луна':'home','Меркурий':'communication','Венера':'love','Марс':'work','Юпитер':'opportunity','Сатурн':'work','Уран':'opportunity','Нептун':'wellbeing','Плутон':'self','ASC':'self','MC':'work'}
PERSONAL={'Солнце','Луна','Меркурий','Венера','Марс'}
SLOW={'Юпитер','Сатурн','Уран','Нептун','Плутон'}
TONE={0:'усиливающий',60:'поддерживающий',90:'напряжённый',120:'поддерживающий',180:'напряжённый'}
HOUSE_PERSPECTIVE={
1:'потребность самостоятельно принимать решения, иначе распределять силы и яснее обозначать собственную роль',
2:'заработок, накопления, цена личного труда и финансовые условия',
3:'переписка, документы, короткие поездки, обучение и важные разговоры',
4:'жильё, домашние обязанности, семейные договорённости и устойчивость дома',
5:'увлечения, дети, романтические встречи и творчество',
6:'рабочий распорядок, повседневные обязанности и распределение нагрузки',
7:'личное и деловое партнёрство, встречи, компромиссы и договорённости',
8:'общие деньги, долги, страховые вопросы и финансовые обязательства',
9:'дальние планы, путешествия, обучение и вопросы мировоззрения',
10:'карьера, репутация, руководство и публичные решения',
11:'друзья, сообщества, коллективные проекты и планы на будущее',
12:'завершение старых дел, уединение, восстановление сил и работа без публичности',
}
BODY_CHARACTER={
'Солнце':'личная позиция и выбор направления',
'Луна':'повседневный ритм, дом и эмоциональная вовлечённость',
'Меркурий':'разговоры, документы и организационные детали',
'Венера':'отношения, ценности и способность договориться',
'Марс':'инициатива, споры и практические действия',
'Юпитер':'расширение возможностей, обучение и финансовые перспективы',
'Сатурн':'долгие обязательства, границы и необходимость выдерживать сроки',
'Уран':'изменение привычного порядка и новые решения',
'Нептун':'ситуации, в которых важно отделить ожидания от фактов',
'Плутон':'глубокий пересмотр контроля, роли и расстановки сил',
'ASC':'личная роль и способ действовать',
'MC':'работа и направление внешних целей',
}

def evidence_theme(hit, natal, *, return_cusps=None, house_of=None):
    # Natal house of target can connect a planet contact to an actual life area.
    h=None
    if hit.get('house') is not None:h=hit.get('house')
    elif hit.get('natal_house') is not None:h=hit.get('natal_house')
    elif house_of and natal.get('cusps') and hit.get('b') in natal.get('raw',{}):
        h=house_of(natal['raw'][hit['b']]['lon'],natal['cusps'])
    # Give the queried natal target priority over a transiting planet's nature.
    name=hit.get('b') or hit.get('a')
    planet_theme=PLANET_THEME.get(name,'self')
    if h and h in HOUSE_THEME:
        ht=HOUSE_THEME[h]
        if ht==planet_theme:return ht
        if planet_theme in ('love','work','money','communication'):
            return planet_theme
        return ht
    return planet_theme

def weighted_hits(hits, natal, *, house_of=None):
    ranked=[]
    for e in hits:
        theme=evidence_theme(e,natal,house_of=house_of)
        angular=1 if e.get('b') in ('ASC','MC') else 0
        slow=1 if e.get('a') in SLOW else 0
        close=max(0.15,1.7-min(float(e.get('orb',2)),3)/2.8)
        score=close+slow*0.5+angular*0.4+(0.15 if e.get('b') in PERSONAL else 0)
        ranked.append((score,theme,e))
    return sorted(ranked,key=lambda r:-r[0])

# Editorial motifs are selected only when the two calculated bodies actually form
# an aspect. They are symbolic examples, not asserted events or feelings.
PAIR_MOTIFS={
 frozenset(('Венера','Сатурн')):('В личной сфере на первый план может выйти разговор о надёжности и конкретных обязательствах.',
   'Если в общении есть паузы, разница возможностей или ограничения временем, может потребоваться прямо обсудить формат участия.'),
 frozenset(('Венера','Марс')):('Отношения могут оживиться через инициативу: сообщение, приглашение или разговор о желаниях.',
   'Желание немедленного ответа способно столкнуться с другим темпом общения; важно не путать напряжённый эпизод с окончательным исходом.'),
 frozenset(('Венера','Уран')):('Может возникнуть желание изменить привычный формат общения или познакомиться с новыми людьми.',
   'Неожиданное изменение планов или потребность в свободе способно осложнить существующую договорённость.'),
 frozenset(('Меркурий','Сатурн')):('Удаётся придать форму давно обсуждаемой задаче: оформить документы, согласовать сроки или распределить ответственность.',
   'В рабочих переговорах или бумагах могут возникнуть задержки; потребуется уточнить условия и перепроверить детали.'),
 frozenset(('Меркурий','Марс')):('Конкретный разговор может ускорить решение: люди готовы обсуждать не намерения, а следующие действия.',
   'Повышается вероятность резких формулировок, спора о деталях или решения, которое потом придётся уточнять.'),
 frozenset(('Меркурий','Юпитер')):('Полезный контакт, учёба или договорённость могут расширить выбор доступных решений.',
   'Масштаб планов и обещаний стоит сверить с расписанием, документами и возможностями.'),
 frozenset(('Солнце','Сатурн')):('Можно оформить долгосрочный план и яснее определить личную ответственность.',
   'Вопрос статуса или обязательств может заставить отказаться от перегрузки и выбрать один приоритет.'),
 frozenset(('Марс','Сатурн')):('Долгую работу проще двигать через последовательные этапы и согласованные сроки.',
   'Инициатива может упираться в регламент, усталость или чужие сроки; прямое давление вряд ли ускорит задачу.'),
 frozenset(('Луна','Венера')):('Бытовые планы, общение с близкими или приятная встреча могут складываться мягче.',
   'Домашние заботы и личные ожидания могут разойтись; разговор о конкретной помощи важнее намёков.'),
 frozenset(('Луна','Сатурн')):('Есть возможность упорядочить домашний график и распределить заботы.',
   'Повседневные обязанности могут ощущаться особенно плотными: потребуется разграничить своё и чужое время.'),
 frozenset(('Солнце','Уран')):('Нестандартное решение может открыть другой подход к уже знакомой задаче.',
   'Может появиться необходимость отойти от старого плана; спешить с окончательным разрывом привычных связей не стоит.'),
 frozenset(('Солнце','Плутон')):('Появляется возможность иначе распределить ответственность и влияние в важном деле.',
   'Вопрос контроля или личной роли может потребовать серьёзного пересмотра договорённостей.'),
}

def contact_story(e):
    pair=PAIR_MOTIFS.get(frozenset((e.get('a'),e.get('b'))))
    if pair:
        return pair[1] if e.get('angle') in (90,180) else pair[0]
    return aspect_meaning(e)

def aspect_meaning(h):
    a,b=h.get('a','планета'),h.get('b','планета');angle=h.get('angle',0)
    first=BODY_CHARACTER.get(a,a.lower());second=BODY_CHARACTER.get(b,b.lower())
    if angle in (60,120):ending='Символически легче найти рабочее сочетание этих тем, но конкретный результат зависит от ваших решений и обстоятельств.'
    elif angle in (90,180):ending='Возможны противоречивые требования: что-то придётся согласовать, пересмотреть или выполнить в два этапа.'
    else:ending='Обе темы становятся заметными одновременно. Это усиливает значимость вопроса, не определяя заранее его исход.'
    return f'Здесь связаны {first} и {second}. {ending}'

def evidence_sentence(e):
    return f"{e['a']} — {e.get('aspect','аспект')} — {e['b']} (орбис {e.get('orb','?')}°)"

def evidence_basis(ranked,limit=2):
    if not ranked:return 'Близких аспектов в выбранном орбисе не обнаружено; сильную событийную формулировку делать нельзя.'
    return 'Основание: '+'; '.join(evidence_sentence(e) for _,_,e in ranked[:limit])+'.'

def climate(ranked):
    if not ranked:return 'ровный по выбранным расчётным критериям: явного преобладания поддерживающих или напряжённых аспектов не выявлено'
    pos=sum(1 for _,_,h in ranked[:7] if h.get('angle') in (60,120))
    hard=sum(1 for _,_,h in ranked[:7] if h.get('angle') in (90,180))
    if pos>hard+1:return 'скорее конструктивный, с возможностью продвигать договорённости и личные планы'
    if hard>pos+1:return 'более требовательный: несколько тем могут одновременно просить усилий и уточнения сроков'
    return 'смешанный: рядом с возможностями сохраняются задачи, которые потребуют внимания'

def theme_section(key, items, *, period_word='период', weak=False):
    t=THEMES[key]
    if not items:
        return {'title':t['name'],'body':f'Эта тема не выделяется среди самых точных показателей выбранного {period_word}. Это не означает, что в реальной жизни здесь ничего не произойдёт: по имеющимся аспектам нельзя уверенно назвать отдельное событие.'}
    heavy=sum(1 for _,_,h in items[:4] if h.get('angle') in (90,180))
    positive=sum(1 for _,_,h in items[:4] if h.get('angle') in (60,120))
    if heavy>positive:body=f'Главный смысл в этой сфере — {t["hard"]}. Возможное проявление: {t["manifest"]}. Не стоит воспринимать отдельную задержку или разговор как окончательный исход.'
    elif positive>heavy:body=f'Здесь проявляется более поддерживающий фон: {t["positive"]}. На практике это может выглядеть как {t["manifest"]}. Речь о возможности, а не о гарантированном событии.'
    else:body=f'В этой сфере соседствуют возможности и необходимость выбора. Может потребоваться {t["manifest"]}. Полезно оценивать результат по конкретным договорённостям, а не по одному удачному или напряжённому моменту.'
    body+=' '+contact_story(items[0][2])
    return {'title':t['name'],'body':body, 'detail':evidence_basis(items)}

def _group(ranked):
    d={k:[] for k in THEMES}
    for item in ranked:d[item[1]].append(item)
    return d

def _render_overview(ranked,period):
    groups=_group(ranked)
    winners=sorted(groups,key=lambda k:sum(score for score,_,_ in groups[k][:3]),reverse=True)
    strong=[k for k in winners if groups[k]]
    if not strong:
        return f'На {period} карта не показывает близких мажорных связей в установленном орбисе. Поэтому выделить одну ведущую жизненную тему и обещать конкретное событие было бы необоснованно.'
    main=strong[:2]
    names=', '.join('«'+THEMES[k]['name'].lower()+'»' for k in main)
    return f'Главный фон {period} связан прежде всего с темами {names}. Общий характер — {climate(ranked)}. Это описание астрологического фона: оно не предсказывает действий других людей и не заменяет реальные обстоятельства.'

def _domain_scenes(ranked,max_n=3):
    groups=_group(ranked)
    ranked_keys=sorted(groups,key=lambda k:sum(score for score,_,_ in groups[k][:2]),reverse=True)
    keys=[k for k in ranked_keys if groups[k]][:max_n]
    if not keys:return 'Нет достаточно близких показателей, чтобы выделить один конкретный сценарий. Для предметного прогноза полезно расширить период или сравнить с другими методами.'
    out=[]
    for i,k in enumerate(keys):
        s=THEMES[k]
        h=groups[k][0][2]
        condition='сложнее обычного' if h.get('angle') in (90,180) else 'может продвинуться' if h.get('angle') in (60,120) else 'может выйти на передний план'
        out.append(f'{i+1}. {s["name"]}: {s["manifest"]}; эта тема {condition}.')
    return ' '.join(out)+' Эти варианты не должны восприниматься как перечень обязательных событий.'

def _window_line(w):
    peak=w.get('peak_day')
    if not peak:return ''
    date=dt.date.fromisoformat(peak)
    start,end=dt.date.fromisoformat(w['start']),dt.date.fromisoformat(w['end'])
    end_text=f'с {start:%d.%m} по {end:%d.%m}' if start!=end else f'около {date:%d.%m}'
    return f'{end_text} — {w["a"]} {w["aspect"]} натального {w["b"]}'

def _calendar_story(windows,day,days_word):
    if not windows:return 'В расчётном диапазоне близких аспектов не обнаружено. Не следует называть точные даты событий без дополнительных оснований.'
    today=dt.date.fromisoformat(day)
    active=[w for w in windows if dt.date.fromisoformat(w['start'])<=today<=dt.date.fromisoformat(w['end'])]
    coming=[w for w in windows if dt.date.fromisoformat(w['start'])>today]
    selected=(active[:2]+coming[:2])[:4]
    if not selected:selected=windows[:3]
    s=f'На {days_word} выделены следующие расчётные интервалы: '+'; '.join(_window_line(w) for w in selected)+'. '
    s+='Пик найден выборкой в полдень, поэтому это ориентир активности аспекта, а не дата гарантированного звонка, встречи или финансового поступления.'
    return s

def transit_consultation(result, c, hits, windows, *, date, mode, house_of):
    ranked=weighted_hits(hits,c,house_of=house_of)
    groups=_group(ranked);period='этого дня' if mode=='day' else 'выбранной даты'
    result['lead']=_render_overview(ranked,period)
    sections=[{'title':'Общий фон и главное', 'body':result['lead'], 'detail':evidence_basis(ranked,3)},
              {'title':'Как это может проявиться', 'body':_domain_scenes(ranked)},
              theme_section('love',groups['love'],period_word='дня' if mode=='day' else 'прогноза'),
              theme_section('work',groups['work']),theme_section('money',groups['money']),
              theme_section('home',groups['home']),theme_section('wellbeing',groups['wellbeing'])]
    slow=[it for it in ranked if it[2].get('a') in SLOW]
    fast=[it for it in ranked if it[2].get('a') not in SLOW]
    sections.append({'title':'Что остаётся фоном, а что проявляется быстрее',
                     'body': ('Долгий фон: '+_domain_scenes(slow,2) if slow else 'В выбранном орбисе нет тесных транзитов медленных планет, которые можно было бы отдельно выделить как долгий фон.')+
                     ' '+('Ближайшие акценты: '+_domain_scenes(fast,2) if fast else 'Сильный короткий акцент по этим данным не выделяется.')})
    sections.append({'title':'Когда фон особенно заметен','body':_calendar_story(windows,date,'ближайшие дни')})
    result['sections']=sections
    result['note']+=' Это символическая трактовка: выводы разделены на краткие и долгие тенденции, а варианты событий не гарантируются.'
    return result

def period_consultation(result, c, windows, *, start,end,house_of):
    selected=sorted(windows,key=lambda w:w['orb'])[:28]
    ranked=weighted_hits(selected,c,house_of=house_of)
    groups=_group(ranked)
    result['lead']=_render_overview(ranked,f'периода {start} — {end}')
    sections=[{'title':'Общая картина периода','body':result['lead'], 'detail':evidence_basis(ranked,3)},
              {'title':'Что может измениться в повседневных событиях','body':_domain_scenes(ranked)},
              theme_section('love',groups['love']),theme_section('work',groups['work']),theme_section('money',groups['money']),
              theme_section('home',groups['home'])]
    slow=[x for x in ranked if x[2]['a'] in SLOW]
    sections.append({'title':'Долгосрочный фон','body':_render_overview(slow,'этого отрезка') if slow else 'В данном отрезке нет близких долгих транзитов в выбранном орбисе. Это не исключает фон более ранних или более поздних периодов.'})
    if windows:
        # Time windows have day-sampled peaks; avoid implying exact instants or settled events.
        choices=sorted(windows,key=lambda w:w['peak_day'])
        # Spread time markers across the period rather than choosing only closest orbs.
        n=min(5,len(choices));indices=sorted(set(round(i*(len(choices)-1)/max(1,n-1)) for i in range(n)))
        lines=[_window_line(choices[i]) for i in indices]
        text='По мере развития периода могут выделяться: '+'; '.join(lines)+'. Даты относятся к аспектам, а не к обязательным событиям; точные часы не определялись.'
    else:text='В отрезке нет достаточно близких аспектов по заданному порогу. Не следует придумывать дату значимого события.'
    sections.append({'title':'Календарь: когда усиливаются отдельные темы','body':text})
    result['sections']=sections
    result['note']+=' Это символическая трактовка. Общий вывод построен только по рассчитанным транзитам; соляр, прогрессии и дирекции не подменяются догадками.'
    return result

def _return_theme(cusp, planets, h):
    main=[n for n,v in planets.items() if v.get('house')==h]
    return main

def return_consultation(result, c, p, cusps, contacts, lum_house, *, body, house_of, start_local,end_local):
    solar=body=='Солнце';period='года' if solar else 'лунного месяца'
    heading=HOUSE_PERSPECTIVE.get(lum_house,'личный ритм и обстоятельства')
    ranked=weighted_hits(contacts,c,house_of=house_of)
    groups=_group(ranked)
    rc=result['return_chart']['planets']
    weights=Counter()
    for name,v in rc.items():
        if v.get('house'):
            weights[HOUSE_THEME[v['house']]]+=(2.2 if name==body else 1.4 if name in ('Венера','Марс','Меркурий','Юпитер','Сатурн') else 0.8)
    for _,theme,h in ranked[:9]:weights[theme]+=1.0
    themes=[k for k,_ in weights.most_common()][:3]
    strong=THEMES[themes[0]]['name'].lower() if themes else 'разные жизненные сферы'
    lead=(f'Цикл с {start_local:%d.%m.%Y} по {end_local:%d.%m.%Y}: основная тема {period} — {heading}. В карте возврата особенно заметна сфера «{strong}». '
          'Это не обещание одного конкретного события: такой фон может проявиться через несколько решений и обстоятельств.') if lum_house else (
          f'В карте возврата этого {period} не удалось вычислить дома для выбранной местности; поэтому нельзя обоснованно назвать ведущую сферу по положению {body.lower()}. Рассмотрим аспекты к наталу.')
    result['lead']=lead
    sections=[{'title':f'Главное в течение {period}', 'body':lead+' '+('Важен не драматичный перелом сам по себе, а практические решения в этой сфере.' if lum_house else '')},
              {'title':'Как период может проявиться в событиях','body':_domain_scenes(ranked,3) if ranked else ('По распределению планет доминируют '+', '.join(THEMES[k]['name'].lower() for k in themes[:2])+'. Это скорее перечень возможных тем года, чем указание на конкретное событие.')},]
    mappings={'love':('Отношения и личная жизнь',('Венера',5,7)),
              'work':('Работа и реализация',('Сатурн',6,10)),
              'money':('Деньги и материальные дела',('Юпитер',2,8)),
              'home':('Дом и семейные вопросы',('Луна',4)),
              'wellbeing':('Ритм жизни и восстановление',('Марс',6,12))}
    for key,(title,members) in mappings.items():
        h_areas=[x for x in members if isinstance(x,int)]
        present=[n for n,v in rc.items() if v.get('house') in h_areas] if cusps else []
        # Prefer actual contacts in this domain; otherwise use relevant occupied return houses.
        theme_matches=groups.get(key,[])
        if theme_matches:
            sec=theme_section(key,theme_matches,period_word=period)
            body_txt=sec['body']
            basis=sec.get('detail','')
        elif present:
            names=', '.join(present[:3]);hvalue=rc[present[0]]['house']
            body_txt=(f'В карте возвращения {names} расположены в домах этой темы. Это делает её заметной в общей картине {period}: '
                      f'возможны {THEMES[key]["manifest"]}. При этом один только дом планеты не позволяет уверенно сказать, какое именно событие состоится.')
            basis=f'Основание: {names} в {hvalue}-м доме карты возврата.'
        else:
            body_txt=(f'Эта сфера не выделяется среди основных показателей карты возврата. Это не прогноз отсутствия событий: '
                      'для детальных сроков и развития ситуации потребуется сопоставление с транзитами и другими методами.')
            basis=''
        sections.append({'title':title,'body':body_txt,'detail':basis})
    if ranked:
        sections.append({'title':'Что добавляют связи с натальной картой','body':(
            'Карта возврата не существует отдельно от рождения: её взаимодействия с наталом показывают, '
            'какие прежние темы могут оказаться особенно заметными. '+
            ' '.join(f'{evidence_sentence(h)}: {contact_story(h)}' for _,_,h in ranked[:3])),
            'detail':'Выбраны наиболее близкие межкартные аспекты, кроме обязательного возвращения светила к себе.'})
    else:
        sections.append({'title':'Связь с наталом','body':'В установленном орбисе нет достаточно тесных контактов к натальным планетам. Не следует подменять их произвольными указаниями на события.'})
    title_t='Границы личного года' if solar else 'Ритм ближайшего месяца'
    sections.append({'title':title_t,'body':(
        f'Цикл начинается {start_local:%d.%m.%Y в %H:%M} и продолжается до {end_local:%d.%m.%Y в %H:%M} по местному времени места возврата. '
        'Этот интервал задаёт фон, но сам по себе не показывает, в какой день произойдёт встреча, перевод денег или смена работы. '
        'Для выделения отдельных дней стоит отдельно рассмотреть транзиты; при сопоставлении с дирекциями и прогрессиями необходимо искать независимое подтверждение темы.')})
    result['sections']=sections
    result['note']+=' Обобщение учитывает дома возврата, положения планет и аспекты к наталу. Срок отдельных событий здесь не рассчитан.'
    return result

def progression_consultation(result,c,moving,matches, *,date,method,house_of):
    ranked=weighted_hits(matches,c,house_of=house_of)
    groups=_group(ranked)
    sun=moving.get('Солнце')
    moon=moving.get('Луна') if c['time_known'] else None
    sign=lambda x: ['Овен','Телец','Близнецы','Рак','Лев','Дева','Весы','Скорпион','Стрелец','Козерог','Водолей','Рыбы'][int(x%360//30)]
    if method=='progression':
        sun_info=f'Прогрессивное Солнце в знаке {sign(sun["lon"])} описывает долгую смену личного акцента.' if sun else ''
        moon_info=f' Прогрессивная Луна в {sign(moon["lon"])} подчёркивает внутренний ритм текущего этапа.' if moon else ' Без точного времени рождения положение прогрессивной Луны намеренно не используется.'
        if moon and c.get('cusps'):
            hh=house_of(moon['lon'],c['cusps'])
            moon_info+=f' В натальных домах она попадает в {hh}-й дом — тема «{HOUSE_PERSPECTIVE[hh]}». Это символическая привязка к натальной системе домов.'
        anchor=sun_info+moon_info
        label='прогрессий'
    else:
        asc=moving.get('ASC');mc=moving.get('MC')
        anchor='Символическая дуга 1° за год постепенно сдвигает исходные позиции. '
        if asc and mc:anchor+=f'Направленный Асцендент в {sign(asc["lon"])} и направленная середина неба в {sign(mc["lon"])} дают дополнительные показатели личной роли и внешних задач.'
        elif not c['time_known']:anchor+='Без времени рождения углы и направленные дома не оцениваются.'
        label='дирекций'
    result['lead']=anchor+' '+_render_overview(ranked,'этой даты')
    secs=[{'title':'Фон жизненного этапа','body':result['lead']},
          {'title':'Что может изменяться постепенно','body':_domain_scenes(ranked,3) if ranked else ('Тесных новых аспектов в установленном орбисе не обнаружено. '+anchor+' Нельзя выводить из этого отсутствие жизненных перемен или дату конкретного события.')},
          theme_section('love',groups['love'],period_word=label),
          theme_section('work',groups['work'],period_word=label),
          theme_section('money',groups['money'],period_word=label)]
    if method=='progression':
        secs.append({'title':'Внутренний ритм и личные решения','body':(
            (f'Прогрессивная Луна сейчас в знаке {sign(moon["lon"])}. Её движение описывает смену внимания и повседневных потребностей, '
             'но не говорит напрямую, что другой человек поступит определённым образом. ' if moon else 'Для оценки прогрессивной Луны потребуется достоверное время рождения. ')+
            ('Есть тесные аспекты прогрессивных планет к наталу; они помогают выделить заметные темы длительного этапа.' if ranked else 'В узком орбисе нет оснований назвать конкретную развязку.'))})
    waves=[]
    for _,theme,h in ranked[:4]:
        if h.get('phase'):
            waves.append(f'{THEMES[theme]["name"]}: показатель {h["phase"]} относительно нынешней даты')
    timing=('По динамике за примерно три месяца до и после даты: '+'; '.join(waves)+'. ' if waves else 'По ближайшему сравнению точных аспектов нет оснований выделить фазу усиления или ослабления. ')
    secs.append({'title':'Когда это может проявиться','body':(
        f'На {date} зафиксировано положение {label}. '+timing+'Эти методы описывают медленно развивающиеся темы, '
        'а не обещают событие сегодня или завтра. Для дат необходимы отдельные точные прохождения и сопоставление с транзитами.'),
        'detail':evidence_basis(ranked,3)})
    result['sections']=secs
    result['note']+=' Основной текст отделяет медленный символический этап от кратких транзитов. Дата точного события не выведена.'
    return result