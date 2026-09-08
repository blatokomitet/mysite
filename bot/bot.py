import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_KEY = os.getenv('API_FOOTBALL_KEY')
TG = f'https://api.telegram.org/bot{TOKEN}'
API = 'https://v3.football.api-sports.io'
MINIAPP = 'https://mysite-three-topaz.vercel.app/'
offset = 0


def tg(method, **kw):
    r = requests.post(f'{TG}/{method}', json=kw, timeout=25)
    r.raise_for_status()
    return r.json()


def football(path, params=None):
    r = requests.get(API + path, headers={'x-apisports-key': API_KEY}, params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json().get('response', [])


def menu(chat):
    tg('sendMessage', chat_id=chat, text='🧠 RUSTAM OS\n\nFootball Intelligence System online.\n\nВыбери модуль:', reply_markup={'keyboard': [['⚽ Football'], ['🧠 AI', '📊 Аналитика'], ['💼 Работа', '⚙️ Настройки'], ['ℹ️ Статус']], 'resize_keyboard': True})


def football_menu(chat):
    tg('sendMessage', chat_id=chat, text='⚽ RUSTAM OS · FOOTBALL INTELLIGENCE\n\nВыбери режим:', reply_markup={'keyboard': [['🔴 Live', '📅 Сегодня'], ['🔎 Анализ', '🎯 Сигналы'], ['📊 Таблицы'], ['⬅️ Назад']], 'resize_keyboard': True})


def today(chat):
    d = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    games = football('/fixtures', {'date': d})[:40]
    if not games:
        return tg('sendMessage', chat_id=chat, text='📅 Сегодня матчей не найдено.')
    buttons = []
    for x in games:
        h = x['teams']['home']['name']; a = x['teams']['away']['name']; fid = x['fixture']['id']
        buttons.append([{'text': f'{h} — {a}', 'callback_data': f'match:{fid}'}])
    tg('sendMessage', chat_id=chat, text=f'📅 МАТЧИ СЕГОДНЯ\n\nНайдено: {len(games)}\n\nВыбери матч:', reply_markup={'inline_keyboard': buttons})


def find_matches(chat, query):
    q = query.strip().lower(); d = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    games = football('/fixtures', {'date': d}); matches = []
    for x in games:
        h = x['teams']['home']['name']; a = x['teams']['away']['name']
        if q in h.lower() or q in a.lower() or q in f'{h} {a}'.lower(): matches.append(x)
    if not matches:
        return tg('sendMessage', chat_id=chat, text=f'❌ Сегодня матч с «{query}» не найден.\n\nПопробуй название одной команды или открой 📅 Сегодня.')
    buttons = [[{'text': f"{x['teams']['home']['name']} — {x['teams']['away']['name']}", 'callback_data': f"match:{x['fixture']['id']}"}] for x in matches[:10]]
    tg('sendMessage', chat_id=chat, text=f'🔎 НАЙДЕНО: {len(matches)}\n\nВыбери матч:', reply_markup={'inline_keyboard': buttons})


def match_card(chat, fid):
    fs = football('/fixtures', {'id': fid})
    if not fs: return tg('sendMessage', chat_id=chat, text='❌ Матч не найден.')
    f = fs[0]; h = f['teams']['home']; a = f['teams']['away']; url = MINIAPP + '?fixture=' + str(fid); dt = f['fixture']['date'].replace('T', ' ')[:16]
    text = f"⚽ {h['name']} — {a['name']}\n🏆 {f['league']['name']}\n🕐 {dt}\n\n🧠 RUSTAM OS подготовил полноценное окно матча.\nФорма · H2H · прогноз · таблица · риск."
    tg('sendMessage', chat_id=chat, text=text, reply_markup={'inline_keyboard': [[{'text': '🚀 ОТКРЫТЬ RUSTAM OS', 'web_app': {'url': url}}]]})


def live(chat):
    games = football('/fixtures', {'live': 'all'})
    if not games: return tg('sendMessage', chat_id=chat, text='🔴 Сейчас live-матчей нет.')
    buttons = []
    for x in games[:30]:
        h = x['teams']['home']['name']; a = x['teams']['away']['name']; hs = x['goals']['home'] or 0; aws = x['goals']['away'] or 0; minute = x['fixture']['status'].get('elapsed') or 0
        buttons.append([{'text': f'{h} {hs}:{aws} {a} · {minute}\'', 'callback_data': f"match:{x['fixture']['id']}"}])
    tg('sendMessage', chat_id=chat, text=f'🔴 LIVE · {len(games)} матчей\n\nВыбери матч:', reply_markup={'inline_keyboard': buttons})


def standings(chat):
    tg('sendMessage', chat_id=chat, text='📊 ТАБЛИЦЫ\n\nВыбери матч через 📅 Сегодня — внутри Mini App будет показана позиция обеих команд и данные их лиги.')


def handle_message(m):
    chat = m['chat']['id']; text = m.get('text', '')
    if text == '/start': return menu(chat)
    if text == '⚽ Football': return football_menu(chat)
    if text == '⬅️ Назад': return menu(chat)
    if text == '📅 Сегодня': return today(chat)
    if text == '🔴 Live': return live(chat)
    if text == '🔎 Анализ': return tg('sendMessage', chat_id=chat, text='🔎 Напиши название команды для поиска сегодняшнего матча.\n\nНапример: Real Madrid')
    if text == '🎯 Сигналы': return tg('sendMessage', chat_id=chat, text='🎯 SIGNAL ENGINE\n\nСначала выбираем реальный матч. Затем RUSTAM OS показывает прогноз и уровень риска в Mini App.')
    if text == '📊 Таблицы': return standings(chat)
    if text == 'ℹ️ Статус': return tg('sendMessage', chat_id=chat, text='🧠 RUSTAM OS ONLINE\n\n⚽ API-Football: ' + ('ONLINE' if API_KEY else 'NO KEY') + '\n🚀 Mini App: ONLINE\n🔐 API key: server-side')
    if text in ('🧠 AI', '📊 Аналитика', '💼 Работа', '⚙️ Настройки'): return tg('sendMessage', chat_id=chat, text='🚧 Этот модуль подключим следующим релизом. Football Intelligence уже работает.')
    if text: return find_matches(chat, text)


print('=================================')
print('🧠 RUSTAM OS FOOTBALL + MINI APP')
print('Telegram polling started')
print('=================================', flush=True)
while True:
    try:
        data = requests.get(f'{TG}/getUpdates', params={'offset': offset, 'timeout': 20}, timeout=30).json()
        for u in data.get('result', []):
            offset = u['update_id'] + 1
            if 'callback_query' in u:
                q = u['callback_query']; tg('answerCallbackQuery', callback_query_id=q['id']); chat = q['message']['chat']['id']; cb = q.get('data', '')
                if cb.startswith('match:'): match_card(chat, cb.split(':', 1)[1])
            elif 'message' in u: handle_message(u['message'])
    except Exception as e:
        print('ERROR', type(e).__name__, str(e), flush=True); time.sleep(5)
