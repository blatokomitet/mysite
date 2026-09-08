import os,time,requests
from dotenv import load_dotenv
load_dotenv()
TOKEN=os.getenv('TELEGRAM_BOT_TOKEN')
API_KEY=os.getenv('API_FOOTBALL_KEY')
TG=f'https://api.telegram.org/bot{TOKEN}'
API='https://v3.football.api-sports.io'
MINIAPP='https://mysite-three-topaz.vercel.app/'
offset=0

def tg(method,**kw):
    r=requests.post(f'{TG}/{method}',json=kw,timeout=25); return r.json()

def football(path,params=None):
    r=requests.get(API+path,headers={'x-apisports-key':API_KEY},params=params or {},timeout=20)
    r.raise_for_status(); j=r.json(); return j.get('response',[])

def menu(chat):
    tg('sendMessage',chat_id=chat,text='🧠 RUSTAM OS\n\nВыбери модуль:',reply_markup={'keyboard':[['⚽ Football'],['🧠 AI','📊 Аналитика'],['💼 Работа','⚙️ Настройки'],['ℹ️ Статус']], 'resize_keyboard':True})

def football_menu(chat):
    tg('sendMessage',chat_id=chat,text='⚽ FOOTBALL INTELLIGENCE\n\nВыбери режим:',reply_markup={'keyboard':[['🔴 Live','📅 Сегодня'],['🔎 Анализ','🎯 Сигналы'],['📊 Таблицы'],['⬅️ Назад']], 'resize_keyboard':True})

def today(chat):
    from datetime import datetime,timezone
    d=datetime.now(timezone.utc).strftime('%Y-%m-%d')
    games=football('/fixtures',{'date':d})
    games=games[:30]
    if not games:return tg('sendMessage',chat_id=chat,text='📅 Сегодня матчей не найдено.')
    buttons=[]
    for x in games:
        h=x['teams']['home']['name'];a=x['teams']['away']['name'];fid=x['fixture']['id'];
        buttons.append([{'text':f"{h} — {a}",'callback_data':f'match:{fid}'}])
    tg('sendMessage',chat_id=chat,text=f'📅 МАТЧИ СЕГОДНЯ\n\nНайдено: {len(games)}\n\nВыбери матч:',reply_markup={'inline_keyboard':buttons})

def match_card(chat,fid):
    fs=football('/fixtures',{'id':fid})
    if not fs:return tg('sendMessage',chat_id=chat,text='❌ Матч не найден.')
    f=fs[0];h=f['teams']['home'];a=f['teams']['away']
    url=MINIAPP+'?fixture='+str(fid)
    text=f"⚽ {h['name']} — {a['name']}\n🏆 {f['league']['name']}\n🕐 {f['fixture']['date'].replace('T',' ')[:16]}\n\n🧠 Открой полноценное окно RUSTAM OS для прогноза, формы, H2H, таблицы и риска."
    tg('sendMessage',chat_id=chat,text=text,reply_markup={'inline_keyboard':[[{'text':'🚀 ОТКРЫТЬ RUSTAM OS','web_app':{'url':url}}]]})

def live(chat):
    games=football('/fixtures',{'live':'all'})
    if not games:return tg('sendMessage',chat_id=chat,text='🔴 Сейчас live-матчей нет.')
    lines=['🔴 LIVE']
    for x in games[:25]:lines.append(f"{x['teams']['home']['name']} {x['goals']['home'] or 0}:{x['goals']['away'] or 0} {x['teams']['away']['name']} · {x['fixture']['status']['elapsed'] or 0}'")
    tg('sendMessage',chat_id=chat,text='\n'.join(lines))

def handle_message(m):
    chat=m['chat']['id'];text=m.get('text','')
    if text in ('/start','⬅️ Назад'):return menu(chat) if text=='/start' else football_menu(chat)
    if text=='⚽ Football':return football_menu(chat)
    if text=='📅 Сегодня':return today(chat)
    if text=='🔴 Live':return live(chat)
    if text=='🔎 Анализ':return tg('sendMessage',chat_id=chat,text='🔎 Сначала открой «📅 Сегодня» и выбери нужный матч.')
    if text in ('🎯 Сигналы','📊 Таблицы'):return tg('sendMessage',chat_id=chat,text='🚧 Модуль готовится к следующему релизу.')
    if text=='ℹ️ Статус':return tg('sendMessage',chat_id=chat,text='🧠 RUSTAM OS ONLINE\n⚽ API-Football: '+('ONLINE' if API_KEY else 'NO KEY')+'\n🚀 Mini App: ONLINE')
    tg('sendMessage',chat_id=chat,text='Используй меню.')

print('=================================');print('🧠 RUSTAM OS + MINI APP');print('Telegram polling started');print('=================================',flush=True)
while True:
    try:
        data=requests.get(f'{TG}/getUpdates',params={'offset':offset,'timeout':20},timeout=30).json()
        for u in data.get('result',[]):
            offset=u['update_id']+1
            if 'callback_query' in u:
                q=u['callback_query'];tg('answerCallbackQuery',callback_query_id=q['id']);chat=q['message']['chat']['id'];cb=q.get('data','')
                if cb.startswith('match:'):match_card(chat,cb.split(':',1)[1])
            elif 'message' in u:handle_message(u['message'])
    except Exception as e:print('ERROR',type(e).__name__,str(e),flush=True);time.sleep(5)
