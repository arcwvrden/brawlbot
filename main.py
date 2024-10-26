from threading import Thread
from telebot import types
import requests, ast, json,telebot,time
API_KEY = 'BSAPIKEY'

botkey = "TGBOTAPIKEY"
bot = telebot.TeleBot(botkey)
database_trophies = {}
databaseupdate = False
database_tags = {}
with open('countries', 'r',encoding='utf-8') as f:
    countrycodes = json.loads(f.read())
with open('brawlers', 'r',encoding='utf-8') as f:
    brawlercodes = json.loads(f.read())
with open('database_tags', 'r', encoding='utf-8') as f:
    database = json.loads(f.read())
with open('database_trophies', 'r', encoding='utf-8') as f:
    database_trophies = json.loads(f.read())

s = requests.Session()

s.headers.update({
    'Authorization' : f'Bearer {API_KEY}'
})


def autodatabaseupdating():
    while True:
        time.sleep(7200)
        global databaseupdate
        databaseupdate = True
        refreshdatabase()
        

@bot.message_handler(commands=['start'])
def startBot(message):
    if databaseupdate:
        types.ReplyKeyboardRemove()
        markup = types.InlineKeyboardMarkup()
        bot.send_message(message.chat.id, f"База обновляется! Обновлено - {int(round(updatestatus,0))}%", parse_mode='html', reply_markup=markup)
        return
    first_mess = f"<b>{message.from_user.first_name}</b>, привет!\nВыбери действие.\n\nПоиск игрока в топах по тегу - перебирает все топы регионов и ищет в них тег игрока. Возвращает регион, бравлера, место и кол-во трофеев на персонаже.\n\nМесто во всех регионах - принимает бравлера, кол-во трофеев и возвращает ваше теоритическое место в различных регионах.\n\nБаза данных обновляется раз в 2 часа."
    markup = types.InlineKeyboardMarkup()
    button_tops = types.InlineKeyboardButton(text = 'Поиск игрока в топах по тегу', callback_data='tops')
    button_place = types.InlineKeyboardButton(text = 'Место в регионах', callback_data='place')
    markup.add(button_tops)
    markup.add(button_place)
    bot.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)
@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    if databaseupdate:
        bot.send_message(call.message.chat.id, f"База обновляется! Обновлено - {int(round(updatestatus,0))}%", parse_mode='html',reply_markup=None)
        return
    
    elif call.data == 'tops':
        bot.edit_message_reply_markup(call.message.chat.id, message_id = call.message.message_id, reply_markup = '')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Введите тег.',reply_markup='')
        bot.register_next_step_handler(call.message, topbetween)
    elif call.data == 'place':
        bot.edit_message_reply_markup(call.message.chat.id, message_id = call.message.message_id, reply_markup = '')
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f'Введите имя бравлера на английском и трофеи через пробел.',reply_markup='')
        bot.register_next_step_handler(call.message, placebetween)
def placebetween(message):
    userinput = message.text.split()
    brawlername = userinput[0].upper()
    if brawlername not in brawlercodes.values():
        bot.send_message(message.chat.id, 'Неправильное имя бравлера!',parse_mode='html')
        return
    trophies = int(userinput[1])
    output = {}
    for i in countrycodes:
        output[i] = place(brawler=brawlername, country=countrycodes[i], troph=trophies)
    
    botoutput = parseplace(output)
    if len(botoutput) > 4096:
        parts = [botoutput[i:i+4096] for i in range(0, len(botoutput), 4096)]
        for part in parts:
            bot.send_message(message.chat.id, part,parse_mode='html')
    else:
        bot.send_message(message.chat.id, botoutput, parse_mode='html')

def topbetween(message):
    if message.text[0] == '/':
        return
    if message.text[0] != '#':
        tag = str('#'+message.text).upper()
    else: tag = message.text.upper()
    print(tag)
    bot.send_message(message.chat.id, 'Идёт поиск...')
    bot.send_message(message.chat.id, parseisintops(isintops(tag)))
def requesttoapi(countrycode,brawlerid:int,brawlername):
    try:
        global database_tags
        request = ast.literal_eval(s.get(f'https://api.brawlstars.com/v1/rankings/{countrycode}/brawlers/{brawlerid}').text)
        total = {}
        for i in request['items']:
            total[i['tag']] = i['trophies']
        if countrycode in database_tags:
            database_tags[countrycode][brawlername] = total
        else: database_tags[countrycode] = {brawlername:total}
        return
    except: print(request)

def refreshdatabase():
    global database_trophies
    global updatestatus
    global databaseupdate
    for country in countrycodes:
        print('new country:', country)
        threads = []
        for brawler in brawlercodes:
            updatestatus = round((list(countrycodes.keys()).index(country)+1)/len(countrycodes),2)*100
            print('updating brawler:', brawlercodes[brawler] , str(brawler)[-2:],'/',len(brawlercodes), 'country: ',country, list(countrycodes.keys()).index(country)+1,'/',len(countrycodes))
            threads.append (Thread(target=requesttoapi,args=(countrycodes[country],brawler,brawlercodes[brawler])))
            threads[-1].start()
            time.sleep(0.013)
    for t in threads:
        t.join()
    with open('database_tags', 'w',encoding='utf-8') as f:
        f.write(str(database_tags).replace("'",'"'))
    for country in database_tags:
        for brawler in database_tags[country]:
            if country not in database_trophies:
                database_trophies[country] = {brawler:list(database_tags[country][brawler].values())}
            else: database_trophies[country][brawler] = list(database_tags[country][brawler].values())
    with open('database_trophies','w', encoding='utf-8') as f:
        f.write(str(database_trophies).replace("'",'"'))
    databaseupdate = False

def parseplace(dictplaces:dict):
    endout = ''
    for i in dictplaces:
        if type(dictplaces[i]) is str:
            endout+='Регион: '+i+' Место: '+dictplaces[i]+'\n'
        elif dictplaces[i][0] == 0:
            endout+='Регион: '+i+' Место: '+str(dictplaces[i][1])+'\n'
        else:
            endout+='Регион: '+i+' Место: с '+str(dictplaces[i][0])+' до '+str(dictplaces[i][1])+'\n'
    return endout

def place(brawler, country, troph):
    try:
        maximum = 0
        minimum = 0
        if troph<database_trophies[country][brawler][-1]:
            return '>200'
        
        for i in range(len(database_trophies[country][brawler])):
            if database_trophies[country][brawler][i]<troph:
                minimum = i+1
                break
            elif maximum==0 and database_trophies[country][brawler][i]==troph:
                maximum = i+1
        return [maximum, minimum] 
    except: return 'Ошибка'

def parseisintops(something:dict):
    if something=={} or something is None:
        return "Игрока нет в топах"
    output = ''
    for i in something:
        something.keys()
        countryname = list(countrycodes.keys())[list(countrycodes.values()).index(i)]
        output+='Регион: '+countryname+'\n'
        for j in something[i]:
            output+='   '+'Бравлер: '+j+' Место: '+str(something[i][j][0])+' Трофеи: '+str(something[i][j][1])+'\n'
    return output

def isintops(seek):
    returning = {}
    for i in database:
        for j in database[i]:
            for n in database[i][j]:
                if seek == n:
                    position = list(database[i][j].keys()).index(seek)+1
                    if i not in returning:
                        returning[i]={j:[position, database[i][j][seek]]}
                    else: returning[i][j] = [position, database[i][j][seek]]
    if returning != {}:
        return returning
    else: return None
Thread(target=autodatabaseupdating).start()
bot.infinity_polling()