# библиотека для работы с базой данных
import sqlite3
# библиотека для работы с телграмм-ботами
import telebot
# библиотека для работы со временем
import datetime
from telebot import types
# библиотека для работы с API электронного дневника
from barsdiary.sync import DiaryApi
# библиотека для получения случайного элемента из списка
from random import choice
# библиотека для типа файлов log
import logging
# библиотека для запуска функции раз в n минут
import schedule


# функция, создающая изначальную базу данных с ДЗ пользователя. получает информацию на ближайшую неделю и заносит в базу данных
def starter(ed_login, ed_password, f_id):
    # обрабатываем исключения, если пользователь ввёл неверный логин или пароль
    try:
        # подключаемся к сайту с нужным логином и паролем
        with DiaryApi.auth_by_login(host="school.vip.edu35.ru", login=ed_login,
                                    password=ed_password) as user_api:
            # получаем сегодняшнюю дату и превращаем её в строку нужного формата
            date_now = str(datetime.date.today())[8:10] + '.' + str(datetime.date.today())[5:7] + '.' + str(
                datetime.date.today())[:4]
            # заводим таймдельту, чтобы получить дату на неделю вперёд
            delta_time = datetime.timedelta(days=7)
            # получаем дату на неделю вперёд
            date_7 = datetime.date.today() + delta_time
            # превращаем её в строку нужного формата
            date_7 = str(date_7)[8:10] + '.' + str(date_7)[5:7] + '.' + str(date_7)[:4]
            # получаем информацию из электронного дневника на ближайшую неделю
            diary = user_api.diary(date_now, date_7).dict()
            # подключаемся к базе данных
            con = sqlite3.connect("users_web.db")
            # заводим курсор для базы данных
            cur = con.cursor()
            # находим id пользователя в таблице users, который нам пишет
            id = cur.execute("""SELECT id FROM users WHERE tg_id=?""", (f_id,)).fetchall()[0][0]
            # проходим циклом по полученным дням
            for i in diary["days"]:
                # заводим перемнную с датой конкретного дня, который мы рассматриваем, для будущего переноса в базу
                date = i['date_str']
                # проверяем, есть ли в этот день есть уроки
                if i["lessons"]:
                    # перебираем содержимое конкретного дня
                    for elem in i['lessons']:
                        # в переменную lesson заводим каждый урок, который у нас есть
                        lesson = elem["discipline"]
                        # в переменную homework заносим домашнее задание, которое у нас есть
                        homework = elem["homework"]
                        # если есть какое то домашнее задание, заносим всю информацию в базу
                        # если ничего не задано, то смысла заносить в базу нет
                        if homework:
                            # заносим информацию в базу по столбикам соответственно
                            cur.execute("""INSERT INTO data(id,date,lesson,homework) VALUES(?,?,?,?)""",
                                        (id, date, lesson, *homework))
                            # публикуем то, что занесли
                            con.commit()
            # прекращаем работу с базой данных
            con.close()
            # возвращаем id пользователя, чтобы потом не выполнять лишние действия с "вытаскиванием" id из базы опять
            return id
    # если возникает ошибка, то пользователь ввёл логин или пароль не так
    except:
        # возвращаем False, чтобы потом сообщить об этом пользователю
        return False


# заводим функцию, проверяющую не появилось ли нового ДЗ в электронном дневнике
def general(flag, ed_login, ed_password):
    # делаем переменную gerb глобальной (нужно будет потом для фунции schedule)
    global gerb
    # получаем сегодняшнюю дату и превращаем её в строку нужного формата
    date_now = str(datetime.date.today())[8:10] + '.' + str(datetime.date.today())[5:7] + '.' + str(
        datetime.date.today())[:4]
    # заводим таймдельту, чтобы получить дату на неделю вперёд
    delta_time = datetime.timedelta(days=7)
    # получаем дату на неделю вперёд
    date_7 = datetime.date.today() + delta_time
    # превращаем её в строку нужного формата
    date_7 = str(date_7)[8:10] + '.' + str(date_7)[5:7] + '.' + str(date_7)[:4]

    # подключаемся к базе данных
    con = sqlite3.connect("users_web.db")
    # и к курсору
    cur = con.cursor()
    # считываем старое домашнее задание, которое уже занесено в базу
    ol_homeworks = cur.execute("""SELECT homework FROM data WHERE id=?""",
                               (flag,)).fetchall()
    # оно возвращается списком кортежей, а нам нужен один общий список
    old_homeworks = ['']
    # поэтому пробегаясь по списку кортежей
    for elem in ol_homeworks:
        # если элемент не пустышка
        if elem[0] != '':
            # мы добавляем его в массив
            old_homeworks.append(elem[0])
    # подключаемся к электронному дневнику через библиотеку
    # обрабатывать исключения не нужно, так как если мы сюда попали, то мы выполняли функцию start
    # значит с данными автоматически всё хорошо
    with DiaryApi.auth_by_login(host="school.vip.edu35.ru", login=ed_login,
                                password=ed_password) as user_api:
        # считываем данные по дням за ближайшие 7 дней
        diary = user_api.diary(date_now, date_7).dict()
        # заводим массивы с: датами,
        dates = []
        # уроками,
        lessons = []
        # домашним заданием
        homeworks = []
        # и массив, который мы будем возвращать
        returner = []
        # перебираем дни
        for i in diary["days"]:
            # если есть уроки,
            if i["lessons"]:
                # то перебираем элементы в этих уроках
                for elem in i['lessons']:
                    # добавляем в массив с датами нужную дату
                    dates.append(i['date_str'])
                    # в массив с уроками нужный урок
                    lessons.append(elem["discipline"])
                    # в массив с ДЗ нужное ДЗ
                    homeworks.append(*elem["homework"])
        # затем перебираем уроки из электронного дневника
        for i in range(len(homeworks)):
            # и если есть такое домашнее задание, которое есть в электронном дневнике, но его нет в базе
            # то это то, что нам и надо
            if homeworks[i] not in old_homeworks:
                # поэтому добавляем в returner массив со всей информацией
                returner.append([dates[i], lessons[i], homeworks[i]])
                # добавляем в базу то, что недоставало
                cur.execute("""INSERT INTO data(id,date,lesson,homework) VALUES(?,?,?,?)""",
                            (flag, dates[i], lessons[i], homeworks[i]))
                # публикуем
                con.commit()
        # прекращаем работу с базой данных
        con.close()
        # добавляем в глобальную переменную gerb то, что появилось
        gerb.append(returner)


# создаём функцию для того, чтобы скидывать человеку ДЗ на день, на который он запрашивает
def hw_on_date(ed_login, ed_password, date):
    # обработка исключений
    # нужно для того, чтобы проверять корректность введенной даты
    # и если дата введена некорректно, то потом сообщить об этом пользователю
    # подключаемся к электронному дневнику через библиотеку
    # обрабатывать исключения не нужно, так как если мы сюда попали, то мы выполняли функцию start
    # значит с данными автоматически всё хорошо
    try:
        with DiaryApi.auth_by_login(host="school.vip.edu35.ru", login=ed_login,
                                    password=ed_password) as user_api:
            diary = user_api.diary(date).dict()
            # заводим массивы с: тем, что будем в конце возвращать,
            returner = []
            # уроками и
            lessons = []
            # и домашним заданием
            homeworks = []
            # перебираем дни
            # перебираем дни
            for i in diary["days"]:
                # если есть уроки,
                if i["lessons"]:
                    # то перебираем элементы в этих уроках
                    for elem in i['lessons']:
                        # если домашнее задание непустое
                        if elem["homework"] != ['']:
                            # то добавляем урок
                            # в соответствующий массив
                            lessons.append(elem["discipline"])
                            # и домашнее задние
                            # в соответсвующий массив
                            homeworks.append(*elem["homework"])
            # присваиваем returner-у значение массива из уроков и домашних заданий
            returner = [lessons, homeworks]
            # возвращаем значение
            return returner
    except:
        return False


# если дата введена неверно
# то возвращаем False
# и затем сообщаем об этом пользователю


# создали бота в FatherBot
# получили токен у FatherBot
# написали его здесь
f = open("token.txt", "r")
bot = telebot.TeleBot(f.readline())
f.close()

# заводим файл для работы с log-ами
logging.basicConfig(level=logging.INFO, filename="py_log.log", filemode="w")


# обрабатываем команду start
@bot.message_handler(commands=['start'])
# функция для обработки команды start
def start(message):
    # сначала создаём инструмент для создания кнопки
    # потом создаём нужные кнопки
    # потом через этот инструмент добавляем их
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Зарегистрироваться")
    btn2 = types.KeyboardButton("/help")
    markup.add(btn1, btn2)
    # отправляем сообщение через бота с добавленными кнопками
    bot.send_message(message.chat.id, text='Привет! Введи команду'.format(message.from_user), reply_markup=markup)
    # добавляем в log то, что пользователь обратился к данной команде
    logging.info("User " + message.from_user.username + " entered the command '/start'")


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    # делаем переменную tg_username глобальной, чтобы она могла использовалаться везде
    global tg_username
    # с помощью специальной функции достаём её значение
    tg_username = message.from_user.username
    # делаем переменную tg_id глобальной, чтобы она могла использовалаться везде
    global tg_id
    # с помощью специальной функции достаём её значение
    tg_id = message.from_user.id
    if message.text == '/help':
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info("User " + message.from_user.username + " entered the command '/help'")
        # сначала создаём инструмент для создания кнопки
        # потом создаём нужные кнопки
        # потом через этот инструмент добавляем их
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Зарегистрироваться")
        btn2 = types.KeyboardButton("/help")
        markup.add(btn1, btn2)
        # отправляем сообщение через бота с добавленными кнопками
        bot.send_message(message.chat.id,
                         text='Это телеграмм бот HomeWorkSender. Он может присылать домашнее задание из '
                              'электронного дневника, как только оно там появится. Нажми на кнопку Зарегистрироваться,'
                              ' введи данные от аккаунта в системе и теперь ты будешь получать рассылку, причём уже'
                              ' через секунду после того, как учитель напишет его.'.format(
                             message.from_user), reply_markup=markup)

    elif message.text == 'Зарегистрироваться':
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info("User " + message.from_user.username + " entered the command 'Register'")
        # отправляем сообщение через бота без добавленных кнопок (они сохраняются с предыдущей команды, где они использовались)
        bot.send_message(message.from_user.id,
                         text='Отлично! Теперь введи свой логин от электронного дневника (нужно найти именно логин от '
                              'электронного дневника, а не от ГосУслуг, если у ты его потерял - обратись к '
                              'преподавателю), только перед ним напиши <<Логин: >> без стрелочек')

    elif message.text[:7] == 'Логин: ':
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info("User " + message.from_user.username + " entered the command 'Login'")
        # делаем переменную login глобальной, чтобы она могла использовалаться везде
        global login
        # из сообщения пользователя изнаём его логин
        login = message.text[7:]
        # отправляем сообщение через бота без добавленных кнопок (они сохраняются с предыдущей команды, где они использовались)
        bot.send_message(message.from_user.id,
                         text='Молодец! Теперь введи свой пароль от электронного дневника (нужно найти именно пароль'
                              ' от электронного дневника, а не от ГосУслуг, если у ты его потерял - обратись к '
                              'преподавателю), только перед ним напиши <<Пароль: >> без стрелочек')

    elif message.text[:8] == 'Пароль: ':
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info("User " + message.from_user.username + " entered the command 'Password'")
        # делаем переменную login глобальной, чтобы она могла использовалаться везде
        global password
        # из сообщения пользователя изнаём его логин
        password = message.text[8:]
        # сначала создаём инструмент для создания кнопки
        # потом создаём нужные кнопки
        # потом через этот инструмент добавляем их
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Да, логин и пароль такие")
        btn2 = types.KeyboardButton("Нет, логин или пароль не такой")
        markup.add(btn1, btn2)
        # отправляем сообщение через бота с добавленными кнопками
        bot.send_message(message.chat.id,
                         text='\n'.join(['Логин: ' + login, 'Пароль: ' + password, 'Всё верно?']).format(
                             message.from_user),
                         reply_markup=markup)

    elif message.text == 'Да, логин и пароль такие':
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info(
            "User " + message.from_user.username + " entered the command 'Yes, login and password are correct'")
        # обрабатываем исключение на случай, если пользователь уже зарегистрирован в системе
        # если он зарегистрирован, то сообщаем, что он уже зарегистрирован
        try:
            # подключаемся к базе данных
            con = sqlite3.connect("users_web.db")
            # поключаемся к курсору
            cur = con.cursor()
            # заполняем информацию с его именем пользователя, айди телеграмма, логин и паролем от электронного дневника
            cur.execute("""INSERT INTO users(username,tg_id,login,password) VALUES(?,?,?,?)""",
                        (tg_username, tg_id, login, password))
            # публикуем
            con.commit()
            # заканчиваем работу с базой данных
            con.close()
            # вызываем функцию starter
            # получаем айди - то, что она возвращает
            flag = starter(login, password, message.from_user.id)
            # если айди получено
            # то выполняем дальше
            if flag != False:
                # создаём второй флаг
                # он нужен для проверки, что все мы не попадали в исключение
                flag2 = True
                # сначала создаём инструмент для создания кнопки
                # потом создаём нужные кнопки
                # потом через этот инструмент добавляем их
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                btn1 = types.KeyboardButton("Узнать ДЗ на конкретную дату!")
                markup.add(btn1)
                # отправляем сообщение через бота с добавленными кнопками
                bot.send_message(message.from_user.id,
                                 text='Молодец! Ты прошёл регистрацию, нажми на единственную конпоку, чтобы узнать домашнее'
                                      ' задание на конкретный день!'.format(
                                     message.from_user), reply_markup=markup)
        except:
            # отправляем сообщение через бота без добавленных кнопок (они сохраняются с предыдущей команды, где они использовались)
            bot.send_message(message.from_user.id,
                             text="Упс! Видимо ты уже зарегистрирован в системе. В этом случае просто жди дальнейших "
                                  "сообщений, так как перерегистрация невозможна.")
            # соответственно в этом случае присваиваем:
            # flag False - мы попали в исключение
            flag2 = False
            # flag True - чтобы попадала в следующий if
            flag = True
        # далее выводим домашнее задание, если пользователь успешно прошёл регистрацию
        if flag != False:
            # если мы не попадали в исключение, так как если мы в него попали, то пользователь уже итак получает сообщения
            if flag2:
                # делаем массив gerb пустым
                gerb = []
                # раз в час вызываем функцию
                schedule.every().hour.do(general, flag=flag, ed_login=login, ed_password=password)
                # присваиваем значение длине
                len_gerb = len(gerb)
                # запускаем бесконечный цикл
                while True:
                    # если длина изменилась, то пишем о пополнении домашнего задания
                    if len(gerb) != len_gerb:
                        # перебираем элементы послднего элемента в массиве (как самого свежего)
                        for elem in gerb[-1]:
                            # открываем случайный из 9 мемов
                            # случайный элемент из списка выбирается с помощью random.choice
                            # затем выбирается картинка из 9
                            img = open("data/" + choice(["2", "3", "4", "5", "6", "7", "8", "9", "10"]) + ".jpg",
                                       'rb')
                            # отправялем мем пользователю
                            bot.send_photo(message.chat.id, img)
                            # отправляем сообщение через бота без добавленных кнопок (они сохраняются с предыдущей команды, где они использовались)
                            # берём первый элемент, это урок
                            # до него добавляем имитацию оповещения
                            # потом пишем дату, на которую задан этот урок
                            # дата хранится в elem[0]
                            # затем пишем пользователю само задание
                            # оно хранится в elem[2]
                            # и, непосредственно, отправляем сообщение пользователю
                            bot.send_message(message.from_user.id,
                                             text="Динь-динь, новое домашнее задание. На этот раз " + elem[1] + " на "
                                                  + elem[
                                                      0] + ". А вот и само задание:                                            "
                                                           "                                           " + elem[2])
                    # функция, чтобы schedule выполнялся непрерывно
                    # она проверяет не прошёл ли ещё час для запуска функции
                    # если прошёл, ты выполняет её
                    schedule.run_pending()
        else:
            # сначала создаём инструмент для создания кнопки
            # потом создаём нужные кнопки
            # потом через этот инструмент добавляем их
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("Зарегистрироваться")
            markup.add(btn1)
            # отправляем сообщение через бота с добавленными кнопками
            bot.send_message(message.from_user.id,
                             text="Упс! Видимо, логин или пароль"
                                  " введены неверно. Обрати внимание, что должен вводить их от ЭЛЕКТРОННОГО ДНЕВНИКА, "
                                  "а не от ГосУслуг. Если ты не знаешь или не помнишь свои данные, то обратись в 210"
                                  " кабинет к Дмитрию Александровичу Бондаренко, он тебе обязательно поможет! "
                                  "Чтобы ввести данные ещё раз нажми на единственную кнопку.".format(message.from_user),
                             reply_markup=markup)

    elif message.text == 'Узнать ДЗ на конкретную дату!':
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info("User " + message.from_user.username + " entered the command 'Find out the homework on a specific"
                                                            " date'")
        # отправляем сообщение через бота без добавленных кнопок (они сохраняются с предыдущей команды, где они использовались)
        bot.send_message(message.chat.id,
                         text='Введи дату, на которую хочешь узнать задание в формате ДД.ММ.ГГГГ')

    elif message.text == 'Нет, логин или пароль не такой':
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info(
            "User " + message.from_user.username + " entered the command 'No, login and password are not correct'")
        # сначала создаём инструмент для создания кнопки
        # потом создаём нужные кнопки
        # потом через этот инструмент добавляем их
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Зарегистрироваться")
        markup.add(btn1)
        # отправляем сообщение через бота с добавленными кнопками
        bot.send_message(message.chat.id,
                         text='Тогда начни сначала! Нажми на единственную кнопку'.format(message.from_user),
                         reply_markup=markup)

    # если получаем от пользователя дату
    elif message.text[6:] in ["2023", "2022", "2021", "2024", "2020", "2019"]:
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info("User " + message.from_user.username + " entered the date")
        # обращаемся к функции
        # получаем из неё массив с урокми и ДЗ за выбранную пользовтелем дату
        h_plus_l = hw_on_date(login, password, message.text)
        print(h_plus_l)
        # если дата введена корректно
        if h_plus_l != False:
            # если ДЗ есть в этот день
            if h_plus_l[0]:
                # открываем случайный из 9 мемов
                # случайный элемент из списка выбирается с помощью random.choice
                # затем выбирается картинка из 9
                img = open("data/" + choice(["2", "3", "4", "5", "6", "7", "8", "9", "10"]) + ".jpg", 'rb')
                # отправляем пользователю изображение, выбранное случайным обзразом
                bot.send_photo(message.chat.id, img)
                # добавляем информацию в log
                # "Добавлено позитивное фото" - о том, что есть ДЗ
                logging.info("The user received a positive photo")
                # заводим текст сообщения, которое будем выводить
                # он будет начинаться на: "Твоё ДЗ на "
                # а затем идёт дата, выбранная пользователем, чтобы выполнить переход через строку там много пробелов
                text_message = "Твоё ДЗ на " + message.text + ":                                                             " \
                                                              "                                                    "
                # запускаем цикл перебирающий
                for i in range(len(h_plus_l[0])):
                    # каждый новый урок и ДЗ прибавляем к сообщению
                    text_message += "✅" + h_plus_l[0][i] + ": " + h_plus_l[1][
                        i] + "                                                                                       " \
                             "                                                                                         "
                # отправляем сообщение через бота без добавленных кнопок (они сохраняются с предыдущей команды, где они использовались)
                # сообщение соотвественно говорит о каждом из уроков
                # а потом пишет ДЗ
                # текст сообщения составлялся в цикле ранее
                bot.send_message(message.chat.id,
                                 text=text_message)
            # если домашнего задания нет на этот день
            # то будет отправляться другая фотка
            # и, соответственно, другое сообщение
            else:
                # открываем фотографию
                # она будет единственной такой, поэтому рандомом не пользуемся
                # имеет номер 1.jpg
                img = open("data/1.jpg", 'rb')
                # бот отправляет потом эту фотографию
                bot.send_photo(message.chat.id, img)
                # добавляем информацию в log
                # "Добавлено негативное фото" - о том, что нет ДЗ
                logging.info("The user received a negative photo")
                # далее отправляем текст, говорящий о том, что уроков в этот день нет
                text_message = "❌На выбранную дату домашнего задания нет!("
                # отправляем сообщение через бота без добавленных кнопок (они сохраняются с предыдущей команды, где они использовались)
                bot.send_message(message.chat.id,
                                 text=text_message)
        else:
            # сначала создаём инструмент для создания кнопки
            # потом создаём нужные кнопки
            # потом через этот инструмент добавляем их
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("Узнать ДЗ на конкретную дату!")
            markup.add(btn1)
            # отправляем сообщение через бота с добавленными кнопками
            bot.send_message(message.from_user.id,
                             text="Введена неверная дата. Для продолжения нажмите на единственную кнопку".format(
                                 message.from_user), reply_markup=markup)

    # если бот получает неизвестное ему сообщение, то он говорит об этом пользователю
    else:
        # добавляем в log то, что пользователь обратился к данной команде
        logging.info("User " + message.from_user.username + " unknown command")
        # сначала создаём инструмент для создания кнопки
        # потом создаём нужные кнопки
        # потом через этот инструмент добавляем их
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Зарегистрироваться")
        btn2 = types.KeyboardButton("/help")
        markup.add(btn1, btn2)
        # отправляем сообщение через бота с добавленными кнопками
        bot.send_message(message.chat.id,
                         text='Это неизвестная для меня команда. Попробуй снова или нажми /help.'.format(
                             message.from_user), reply_markup=markup)


# эта функция говорит о том, что бот работает без отсановок с интервалом 0
bot.polling(none_stop=True, interval=0)
