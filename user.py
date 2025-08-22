from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatMember,
    WebAppInfo
)
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ChatMemberStatus

import json
from general import *
import content

connect_mysql = Mysql(db.USER, db.PASS, db.HOST, db.DATABASE)

back_menu = [[InlineKeyboardButton(text="В главное меню", callback_data=str(USER_MENU))]]
cancel = [[InlineKeyboardButton(text="Отмена", callback_data=str(CANCEL))]]
skip = [[InlineKeyboardButton(text="Пропустить", callback_data=str(SKIP))]]

def check_autorize(func):
    """Данная функция нужна для того чтобы моментально впустить пользователя в бота,
    если его сообщение все еще имеет старую информацию о необходимости зарегистрироваться"""
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        result = connect_mysql("SELECT * FROM users WHERE user_id = %s", (user_id,))
        if not result:
            return await func(update, context, *args, **kwargs)
        else:
            return await start(update, context)
    return wrapped


# START / FIRST START / MENU
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    user_id = update.effective_user.id
    result = connect_mysql("SELECT * FROM users WHERE user_id = %s", (user_id,))
    print(result)
    if not result:
        data = update.effective_message.text
        context.user_data['data invite control'] = data
        await consent(update, context)
    else:
        # юзер меню
        # bonuses = result[0][3] # количество бонусов пользователя
        bonuses = dict(connect_mysql("SELECT * FROM bonuses"))
        check = bonuses.get(bonustype.CHECK)
        review = bonuses.get(bonustype.REVIEW)
        text = content.user.MAINMENU % (check, review)
        keyboard = [[InlineKeyboardButton("Пройти тест", callback_data=str(SOLO_TEST))],
                    [InlineKeyboardButton("Начислить бонусы", callback_data=str(GET_BONUSES))],
                    [InlineKeyboardButton("Обменять бонусы на подарки",
                                          web_app=WebAppInfo(WEBURL))],
                    [InlineKeyboardButton("Написать нам", callback_data=str(SUPPORT))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await construct_message(update, text, reply_markup)
    
    # print(persistence.callback_data)
    return ConversationHandler.END

async def invite_control(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    data = data.split()
    if len(data) == 2:
        try:
            from_id = data[1]
            to_id = update.effective_user.id
            have = connect_mysql("SELECT * FROM invited WHERE to_id = %s", (to_id))
            if not have:
                connect_mysql("INSERT INTO invited (from_id, to_id) VALUES (%s, %s)", (from_id, to_id))
                bonuses_invite = dict(connect_mysql("SELECT * FROM bonuses")).get(bonustype.INVITE)
                connect_mysql("UPDATE users SET bonuses = bonuses + %s, lastmove = %s WHERE user_id = %s",
                                                        (bonuses_invite, now_time(), from_id))
                text = content.user.REFFERAL_LINK_USED % bonuses_invite
                await context.bot.send_message(chat_id=from_id, text=text)
        except:
            print("Проблема с реферальной ссылкой")

@check_autorize
async def consent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Да", callback_data=str(YES_CONSENT))],
                [InlineKeyboardButton("Нет", callback_data=str(NO_CONSENT))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text=content.user.CONSENT,
                                    reply_markup=reply_markup)
    return ConversationHandler.END

@check_autorize
async def rejected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Вернуться", callback_data=str(COMEBACK))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(text=content.user.REJECTED,
                                    reply_markup=reply_markup)
    return COMEBACK

@check_autorize
async def share_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[KeyboardButton("Поделиться номером", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    # await update.message.edit_reply_markup(reply_markup=None)
    await update.callback_query.answer()
    await update.effective_user.send_message(text=content.user.SHARE_PHONE,
                                    reply_markup=reply_markup)
    print('share_phone')
    return SHARE_PHONE

@check_autorize
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username
    if update.message.contact:
        user_id_contact = update.message.contact.user_id
        phone = update.message.contact.phone_number
        # username = update.effective_user.username
        if not user_id_contact == user_id:
            text = "Кажется это не ваш контакт.\nПопробуйте снова:"
            await update.effective_user.send_message(text=text)
            return SHARE_PHONE
    else:
        phone = update.effective_message.text
        # Максимальная длина номера в мире - 18 цифр (вкл-я код страны)
        # Минимальная длина номера в мире - 6 (вкл-я код страны)
        phone = phone.replace("+", "")
        if not phone.isdigit() and len(phone) >= 6 and len(phone) <= 18:
            text = "Некорректный ввод номера.\nПопробуйте снова:"
            await update.effective_user.send_message(text=text)
            return SHARE_PHONE
    bonuses = dict(connect_mysql("SELECT * FROM bonuses"))
    welcome_bonus = bonuses.get(bonustype.WELCOME)
    follow_bonus = bonuses.get(bonustype.FOLLOW)
    connect_mysql("INSERT INTO users (user_id, username, phone, bonuses, lastmove) VALUES (%s, %s, %s, %s, %s)", (user_id, username, phone, welcome_bonus, now_time()))
    # так же создаем строчку пользователя в таблице, где фиксируются полученные подарки:
    connect_mysql("INSERT INTO purchased_gifts (user_id) VALUES (%s)", (user_id,))
    # connect_mysql("UPDATE users SET bonuses = bonuses + %s WHERE user_id = %s", (bonus, user_id))

    # Здесь нужно любое сообщение, чтобы удалить клавиатуру
    text = "Добро пожаловать!"
    text = content.user.WELCOME
    await update.effective_user.send_message(text=text,
                                             reply_markup=ReplyKeyboardRemove())
    
    # Если все ок, то отправляем сообщение розыгрыша (Raffle)
    text = content.user.RAFFLE % (welcome_bonus, follow_bonus, BOT_NAME, BOT_NAME)
    image = PLUG
    keyboard = [[InlineKeyboardButton("Подписаться на канал", url=CHANNEL_LINK)],
                [InlineKeyboardButton("Участвую!", callback_data=str(RAFFLE_ENTRY))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_user.send_photo(caption=text, reply_markup=reply_markup,
                                           photo=image)
    # И следом меню:
    await start(update, context)
    # И следом проверка на инвайт
    data = context.user_data.get('data invite control')
    if data:
        await invite_control(update, context, data)

    return ConversationHandler.END

async def raffle_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    query = update.callback_query
    # Проверяем действительно ли пользователь подписался на канал
    chat_member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
    if chat_member.status in (ChatMemberStatus.MEMBER,
                                ChatMemberStatus.OWNER,
                                    ChatMemberStatus.ADMINISTRATOR):
        # await query.answer()
        # добавляем в список участников
        result = connect_mysql("INSERT IGNORE INTO raffle_users (user_id) VALUES (%s)", (user_id,))
        if not result: 
            text = "Не удалось добавить вас в список участников, попробуйте снова или обратитесь в поддержку"
            await query.answer(text=text, show_alert=True)
        else:
            text = content.user.RAFFLE_ENTRY
            await query.answer(text=text, show_alert=True)
    else:
        # Уведомление о том, что пользователь не подписан на канал
        text = content.user.RAFFLE_ALERT
        await query.answer(text=text, show_alert=True)

async def cancel_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = InlineKeyboardMarkup(back_menu)
    text = "Операция отменена"
    await construct_message(update, text=text, reply_markup=reply_markup)
    return ConversationHandler.END


# SOLO TEST
async def test_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['solo test'] = False

    text = content.user.TEST_PREVIEW
    keyboard = [[InlineKeyboardButton("Пройти тест", callback_data=str(TAKE_TEST))]] + back_menu
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text, reply_markup)
    return TEST_PREVIEW

async def test_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    # Настройки при запуске теста
    with open('solo-test.json', 'r', encoding='utf-8') as file:
        user_data['test content'] = json.load(file)
    products = user_data['test content']["Products"]
    user_data['test results'] = {n:0 for n, _ in products.items()}
    user_data['test page'] = 0
    user_data['products'] = False
    user_data['len questions'] = len(user_data['test content']['Questions'])
    return await test_process(update, context)

async def test_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    query = update.callback_query
    if user_data.get("test page"):
        # Подбираем результаты предыдущего этапа
        selected = query.data.split('-')[1:]
        for n in selected:
            user_data['test results'][n] += 1

    # Если предыдущий вопрос был последним, то тормозим тест
    if user_data['len questions'] == user_data['test page']:
        return await test_final(update, context)

    test = user_data['test content']
    user_data['test page'] += 1
    stage = test.get("Questions").get(str(user_data['test page']))
    text = stage.pop("Quest")
    image = stage.pop("Image")
    keyboard = []
    score = 0
    for letter, other in stage.items():
        text += f"\n{letter}: {other.get('Answer')}" # A: Ответ n ...
        nums = "-".join([str(n) for n in other.get("Products")])
        if score % 2 == 0:
            keyboard.append([InlineKeyboardButton(letter,
                                callback_data=f"{letter}-{nums}")])
        else:
            keyboard[-1].append(InlineKeyboardButton(letter,
                                callback_data=f"{letter}-{nums}"))
        score += 1

    reply_markup = InlineKeyboardMarkup(keyboard)

    await construct_message(update, text, reply_markup, image)
    return PROCESS_TEST

async def message_to_admins(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    admins = connect_mysql("SELECT * FROM managers;")
    for admin in admins:
        try:
            await context.bot.send_message(chat_id=admin[0], text=text)
        except:
            pass

async def test_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_id = update.effective_user.id
    # Определяем какой продукт набрал большее количество баллов
    results = user_data['test results'] # {'1': 2, '2': 2, ...}
    l = [[k,v] for k, v in results.items()] # [['1', 2], ['2', 2], ...]
    product_won = max(l, key=lambda n: n[-1]) # ['1', 2]
    # Проверяем на ничью, в случае любой ничьи побеждает 5й продукт
    l.remove(product_won)
    check_second = max(l, key=lambda n: n[-1])
    if check_second[-1] == product_won[-1]:
        number = "5"
    else:
        number = product_won[0]
    # Название продукта и его текст
    results = user_data["test content"]["Results"][number] 
    for name, desc in results.items():
        text = f"{name}\n\n{desc}"


    reply_markup = InlineKeyboardMarkup(back_menu)

    # Отправляем текст результата теста:
    await construct_message(update, text)

    # Блокируем получение промокода при повторном прохождении теста:
    used_before = connect_mysql("SELECT * FROM users_promocodes WHERE user_id = %s", (user_id,))
    if used_before: 
        await update.effective_user.send_message("Вернуться в меню:",
                                                 reply_markup=reply_markup)
        return ConversationHandler.END


    # Ищем неиспользованные промокоды
    promocodes = connect_mysql("SELECT * FROM promocodes WHERE status = 0;")
    
    if promocodes:
        promocode = promocodes[0][0]
        text = content.user.TEST_FINAL % promocode
        connect_mysql("UPDATE promocodes SET status = 1 WHERE code = %s", (promocode,))
        # Регистрируем получение промокода
        connect_mysql("INSERT INTO users_promocodes (user_id, promocode) VALUES (%s, %s)",
                                    (user_id, promocode))
    else:
        # ни одного свободного промокода нет, сигналим админам:
        text = content.user.TEST_FINAL_NONE_PROMOCODE
        text_admins = "Пользователь не смог получить промокод после прохождения теста.\nНет ни одного неиспользованного промокода в таблице."
        await message_to_admins(update, context, text_admins)

    await update.effective_user.send_message(text=text)
    await update.effective_user.send_message(text="Вернуться в меню:", reply_markup=reply_markup)

    # Регистрируем в бд, кто и какой тест прошел
    test_id = 1 # тест всего один
    connect_mysql("INSERT INTO users_tests (user_id, user_test) VALUES (%s, %s)",
                                        (user_id, test_id))
    
    connect_mysql("UPDATE users SET lastmove = %s WHERE user_id = %s",
                                        (now_time(), user_id))
    
    return ConversationHandler.END


# BONUS MENU
async def bonus_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Чек покупки", callback_data=str(CHECK))],
        [InlineKeyboardButton("Отзыв", callback_data=str(REVIEW))],
        [InlineKeyboardButton("Подписка на канал", callback_data=str(FOLLOW))],
        [InlineKeyboardButton("Пригласить друга", callback_data=str(REFERRAL))],] + back_menu
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = content.user.BONUS_MENU
    await construct_message(update, text, reply_markup)


# check
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = content.user.SENDING_CHECK
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return WAIT_CHECK

def qr_data_correct(data: str) -> Union[dict, None]:
    # data = "t=20250618T162220&s=234.00&fn=7380440801036664&i=123309&fp=274542987&n=1"
    try:
        data = data.split('&')
        data = dict([x.split('=') for x in data])
        assert len(data) == 6
        return data
        # return {'t': '20250618T162220', 's': '234.00', 'fn': '7380440801036664', 'i': '123309', 'fp': '274542987', 'n': '1'}
    except:
        return None

def qr_code_verification(data: str):
    '''Проверка чека'''
    data = qr_data_correct(data)
    if not data: return False

    # проверяем чек по офд, и если он реальный, 
    # То надо глянуть какая была покупка:
    # (по инн ? или по названию покупки включающее 'Lovix'?)

    # Если все ок, то возвращаем True, если нет False
    return True

async def check_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    pdf_file = await get_pdf(update, Paths.CHECKS)
    img_file = await get_image(update, Paths.CHECKS)
    if pdf_file:
        images = extract_images_from_pdf(pdf_path=pdf_file,
                                output_dir=Paths.EXTRACT)
    else:
        images = [img_file]
    file_path = pdf_file or img_file

    data_one = None
    qr_code_find = False
    get_bonuses = 0
    d = dict(connect_mysql("SELECT * FROM bonuses"))
    plus = d.get(bonustype.CHECK)
    for img in images:
        qr_data = find_qr_in_image(img)
        if qr_data:
            print("Найденные QR-коды:")
            for data in qr_data:
                print(data)
                duplicate = connect_mysql("SELECT * FROM checks WHERE data = %s", (data,))
                verification = qr_code_verification(data)
                if duplicate or not verification:
                    continue
                get_bonuses += plus
                # записываем данные файла в бд
                connect_mysql("INSERT INTO checks VALUES (%s, %s, %s)",
                                    (user_id, file_path, data))
            qr_code_find = True
        else:
            print("QR-коды не найдены.")
    
    bonuses_score = connect_mysql("SELECT * FROM users WHERE user_id = %s", (user_id,))[0][3]

    if get_bonuses:
        # Один из отправленных чеков был уже ранее использован
        new_bonuses_value = bonuses_score + get_bonuses
        connect_mysql("UPDATE users SET bonuses = %s, lastmove = %s WHERE user_id = %s",
                      (new_bonuses_value, now_time(), user_id))
        text = content.user.CHECK_ACCEPT % (get_bonuses, new_bonuses_value)
    elif not qr_code_find:
        text = content.user.QR_NOT_FOUND
        connect_mysql("INSERT INTO checks_aborted (user_id, path) VALUES (%s, %s)", (user_id, file_path))
    else:
        text = content.user.CHECK_NOT_ACCEPT
        connect_mysql("INSERT INTO checks_aborted (user_id, path) VALUES (%s, %s)", (user_id, file_path))
        
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return WAIT_CHECK

async def review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = content.user.SENDING_FEEDBACK_SCREEN
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return WAIT_REVIEW

async def review_sent_looped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    image = await get_image(update, Paths.REVIEWS)
    res = connect_mysql("INSERT INTO reviews (user_id, image) VALUES (%s, %s)",
                                                        (user_id, image))
    id = res.get('lastrowid')
    text = content.user.FEEDBACK_LAST_STEP
    reply_markup = InlineKeyboardMarkup(back_menu)
    admins = connect_mysql("SELECT * FROM managers")
    await construct_message(update, text, reply_markup)

    for admin in admins:
        a_text = content.admin.NEW_FEEDBACK_SCREEN % id
        a_keyboard = [[InlineKeyboardButton("Подтвердить",
                                            callback_data=f"{REVIEW_CONFIRM_NOTIFICATION}-{id}")]]
        a_reply_markup = InlineKeyboardMarkup(a_keyboard)
        await context.bot.send_photo(chat_id=admin[0], caption=a_text,
                                     photo=image, reply_markup=a_reply_markup)

    return WAIT_REVIEW

async def follow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = content.user.FOLLOW_CHANNEL
    keyboard = [[InlineKeyboardButton("Подписаться на канал", url=CHANNEL_LINK)]] + back_menu
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text, reply_markup)

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    link = f"t.me/{BOT_NAME}?start={user_id}"
    text = content.user.REFERRAL_LINK % link
    # text = 'text'
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup, parse_mode="Markdown")


# support
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    reply_markup = InlineKeyboardMarkup(back_menu)
    text = content.user.MESSAGE_TO_MANAGER
    await construct_message(update, text, reply_markup)
    return SUPPORT

async def support_img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_data['application text'] = update.message.text
    text = content.user.IMAGE_OR_SKIP
    reply_markup = InlineKeyboardMarkup(skip)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return SUPPORT_IMG

async def support_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    text = "Какой способ связи вам предпочтительнее?"
    keyboard = [[InlineKeyboardButton('Почта', callback_data=str(EMAIL))],
                [InlineKeyboardButton('Позвоните мне!', callback_data=str(PHONE))]]
    # Проверка, есть ли у человека username в телеграме
    if update.effective_user.username:
        keyboard = [[InlineKeyboardButton('Телеграм', callback_data=str(TELEGRAM))]] + keyboard

    reply_markup = InlineKeyboardMarkup(keyboard)
    user_data['application photo'] = await get_image(update, path=Paths.APPLICATIONS)
    await construct_message(update, text, reply_markup)

    return SUPPORT_CONTACT

async def send_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == str(PHONE):
        text = "Укажите ваш номер телефона"
    else:
        text = "Укажите вашу почту"
    
    await update.callback_query.message.edit_text(text=text)
    return SEND_CONTACT

async def view_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    photo = user_data['application photo']
    user_id = update.effective_chat.id
    query = update.callback_query
    text_application = user_data['application text']
    text = "Ваша заявка:\n\n" + text_application
    keyboard = [[InlineKeyboardButton('Отправить', callback_data=str(SEND_APPLICATION))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query: # контакты записываем
        await query.answer()
        # Проверка есть ли у человека username
        if not update.effective_user.username:
            text = "У вас нет телеграм-username.\nНеобходимо добавить уникальный username в настройках телеграма или выбрать другой тип связи. Попробуйте заново."
            await context.bot.send_photo(chat_id=user_id, caption=text)
            return ConversationHandler.END
        user_data['application contact'] = '@' + update.effective_user.username      
    else:
        user_data['application contact'] = update.message.text

    if photo:
        await context.bot.send_photo(chat_id=user_id, caption=text,
                                     photo=photo, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=user_id,
                                       text=text, reply_markup=reply_markup)
    return APPLICATION_COMPLETE

async def application_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_id = update.effective_chat.id
    query = update.callback_query
    await query.answer()
    image = user_data['application photo']
    text = user_data['application text']
    contact = user_data['application contact']

    result = connect_mysql("INSERT INTO applications (user_id, message, image, contact) VALUES (%s, %s, %s, %s)", (user_id, text, image, contact))

    text_complete = "Ваша заявка отправлена и теперь в обработке.\nОжидайте ответа от менеджера"
    reply_markup = InlineKeyboardMarkup(back_menu)

    await update.callback_query.edit_message_reply_markup(reply_markup=None)
    await update.callback_query.message.reply_text(text=text_complete,
                                                   reply_markup=reply_markup)
    managers = connect_mysql("SELECT * FROM managers")
    managers = [manager[0] for manager in managers]
    id = result.get('lastrowid')
    text=f'Поступило новое обращение от пользователя\nНомер заявки: {id}'
    for chat_id in managers:
        try:
            await context.bot.send_message(text=text, chat_id=chat_id)
        except: pass
    return ConversationHandler.END


# проверка подписки
def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[tuple[bool, bool]]:
    """
    Принимает экземпляр ChatMemberUpdated и извлекает информацию о том, был ли участником
    чата «old_chat_member» и является ли участником
    чата «new_chat_member». Возвращает None, если
    статус не изменился
    """
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))
    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member

async def greet_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = extract_status_change(update.chat_member)
    if result is None:
        return

    was_member, is_member = result

    if not is_member:
        return
    
    await follow_alert(update, context)

async def follow_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверяем получал ли пользователь ранее бонусы за подписку
    и если нет, то даем бонусы и отправляем уведомление об этом"""
    user_id = update.chat_member.from_user.id

    already_sub = connect_mysql("SELECT * FROM follow_users WHERE user_id = %s", (user_id,))
    authorize_in_bot = connect_mysql("SELECT * FROM users WHERE user_id = %s", (user_id,))
    if already_sub or not authorize_in_bot:
        return
    
    connect_mysql("INSERT INTO follow_users (user_id) VALUES (%s)", (user_id,))
    follow_bonuses = dict(connect_mysql("SELECT * FROM bonuses")).get(bonustype.FOLLOW)
    connect_mysql("UPDATE users SET bonuses = bonuses + %s, lastmove = %s WHERE user_id = %s",
                                                (follow_bonuses, now_time(), user_id))
    
    reply_markup = InlineKeyboardMarkup(back_menu)
    text = content.user.FOLLOW_ALERT % follow_bonuses

    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

async def exchange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    username = update.effective_user.username
    query_data = query.data.split('-')
    title, bonuses, tag = query_data[1], int(query_data[2]), query_data[3]
    user = connect_mysql("SELECT * FROM users WHERE user_id = %s", (user_id,))
    if not user: return
    else: user = user[0]
    phone, bonuses_balance = user[2], user[3]
    if bonuses_balance >= bonuses:
        bonuses_balance -= bonuses # оставшийся счет
        connect_mysql(f"UPDATE purchased_gifts SET `{tag}` = 1 WHERE user_id = {user_id};")
        purchased_gifts = connect_mysql(
            "SELECT * FROM purchased_gifts WHERE user_id = %s", (user_id,))[0][1:]
        # print(purchased_gifts) # [user_id, 0,0,0,0,0]
        text = content.user.GIFT_ACCEPTED % {"title": title, "bonuses": bonuses}
        await query.answer()
        await query.edit_message_caption(caption=text, reply_markup=None)
        reply_markup = InlineKeyboardMarkup(back_menu)
        # Ищем какой подарок пользователь еще не приобрел, далее предлагаем ему этот подарок
        i = 0
        for _, next_gift_info in GIFTS_INFO.items():
            print('next gift', _, next_gift_info)
            if not purchased_gifts[i]:
                break
            i += 1
        # Если у пользователя недостаточно бонусов до следующего подарка:
        if bonuses_balance < next_gift_info[1]: 
            text = content.user.AFTER_GIFT_0 % (bonuses_balance,
                                                next_gift_info[1] - bonuses_balance,
                                                next_gift_info[0])
            await update.effective_user.send_message(text=text, reply_markup=reply_markup)
        else: # Если у пользователя хватает бонусов
            text = content.user.AFTER_GIFT_1 % (bonuses_balance,
                                                next_gift_info[0],
                                                next_gift_info[1])
            await update.effective_user.send_message(text=text, reply_markup=reply_markup)

        # Рассылка всем менеджерам
        d = {"title": title, "bonuses": bonuses, "phone": phone, "username": username}
        text = content.admin.ALERT_GIFT_ACTIVATED % d
        admins = connect_mysql("SELECT * FROM managers")
        got_it = False
        print("admins", admins)
        if admins:
            for admin in admins:
                try:
                    await context.bot.send_message(chat_id=admin[0],
                                                   text=text)
                    got_it = True
                except:
                    pass
        # И только в самом конце меняем в базе данных баланс пользователю
        if got_it: # Если хоть кто-то из админов получил уведомления
            connect_mysql("UPDATE users SET bonuses = %s " \
                          "WHERE user_id = %s",
                            (bonuses_balance, user_id))
            connect_mysql("UPDATE purchased_gifts " \
                          f"SET `{tag}` = 1 WHERE user_id = {user_id};")
    else:
        await query.answer(text="Недостаточно бонусов", show_alert=True)


# fallbacks
from admin import admin # данный импорт нужен именно здесь
fallbacks = [CallbackQueryHandler(admin, pattern=f"^{ADMIN_MENU}$"),
               CallbackQueryHandler(start, pattern=f"^{USER_MENU}$"),
               CallbackQueryHandler(cancel_message, pattern=f"^{CANCEL}$"),
               CommandHandler("admin", admin),
               CommandHandler("start", start)]

# Conversations
conv_first_run = ConversationHandler(
    entry_points=[CallbackQueryHandler(share_phone, pattern=f"^{YES_CONSENT}$"),
                  CallbackQueryHandler(rejected, pattern=f"^{NO_CONSENT}$")],
    states={
        COMEBACK: [CallbackQueryHandler(consent, pattern=f"^{COMEBACK}$")],
        SHARE_PHONE: [MessageHandler(filters.CONTACT, contact),
                      MessageHandler(filters.TEXT & ~filters.COMMAND,
                                                        contact)],       
    },
    fallbacks=fallbacks
)

conv_solotest = ConversationHandler(
    entry_points=[CallbackQueryHandler(test_preview,
                                pattern=f"^{SOLO_TEST}$")],
    states={
        TEST_PREVIEW:
            [CallbackQueryHandler(test_run,
                                    pattern=f"^{TAKE_TEST}$")],
        PROCESS_TEST:
            [CallbackQueryHandler(test_process, # ^({SOME}-)
                                    pattern="|".join([f"^({l}-)" for l in LETTERS]))]
    },
    fallbacks=fallbacks
)

conv_check = ConversationHandler(
    entry_points=[CallbackQueryHandler(check,
                    pattern=f"^{CHECK}$")],
    states={
        WAIT_CHECK:
            [MessageHandler(filters.Document.PDF |
                                filters.Document.IMAGE |
                                    filters.PHOTO, 
                                        check_analysis)]
    },
    fallbacks=fallbacks
)

conv_review = ConversationHandler(
    entry_points=[CallbackQueryHandler(review,
                    pattern=f"^{REVIEW}$")],
    states={
        WAIT_REVIEW:
            [MessageHandler(filters.Document.IMAGE | filters.PHOTO, 
                                        review_sent_looped)]
    },
    fallbacks=fallbacks
)

conv_support = ConversationHandler(
        entry_points=[CallbackQueryHandler(support, pattern=f"^{SUPPORT}$")],
        states={
            SUPPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_img)],
            SUPPORT_IMG: [MessageHandler(filters.Document.IMAGE & ~filters.COMMAND, support_contact),
                          MessageHandler(filters.PHOTO & ~filters.COMMAND, support_contact),
                   CallbackQueryHandler(support_contact, pattern=f"^{SKIP}$")],
            SUPPORT_CONTACT: [CallbackQueryHandler(send_contact, pattern=f"^{EMAIL}$|^{PHONE}$"),
                       CallbackQueryHandler(view_application, pattern=f"^{TELEGRAM}$")],
            SEND_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_application)],
            APPLICATION_COMPLETE: 
                    [CallbackQueryHandler(application_send, pattern=f"^{SEND_APPLICATION}$")],
            FALL: [],
        },
        fallbacks=fallbacks
    )

# conv_support = ConversationHandler(
#     entry_points=[CallbackQueryHandler(support,
#                     pattern=f"^{SUPPORT}$")],
#     states={
        
#     },
#     fallbacks=fallbacks
# )