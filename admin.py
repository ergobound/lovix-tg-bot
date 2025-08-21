from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    error
)
from telegram.ext import (
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from pandas import read_excel
from openpyxl import Workbook
import logging, sys
from functools import wraps
from constants import *
from general import *
import content

connect_mysql = Mysql(db.USER, db.PASS, db.HOST, db.DATABASE)

back_menu = [[InlineKeyboardButton(text="В главное меню", callback_data=str(ADMIN_MENU))]]
user_menu = [[InlineKeyboardButton(text="В главное меню", callback_data=str(USER_MENU))]]
cancel = [[InlineKeyboardButton(text="Отмена", callback_data=str(CANCEL))]]
skip = [[InlineKeyboardButton(text="Пропустить", callback_data=str(SKIP))]]

def restricted(func):
    """Проверка статуса админа"""
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        result = connect_mysql("SELECT * FROM managers WHERE user_id = %s", (user_id,))
        if result or user_id in ADMINS:
            return await func(update, context, *args, **kwargs) # Все впорядке
        else:
            await update.effective_message.reply_text('Извините, доступ к админ-панели закрыт.')
            logging.info(f"Неавторизованный доступ запрещен для {user_id}.")
    return wrapped

@restricted
async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Изменить баланс пользователя"""
    try:
        msg = update.message.text
        msg = msg.split()
        user_id, bonuses = msg[1], msg[2]
        connect_mysql("UPDATE users SET bonuses = %s WHERE user_id = %s", (bonuses, user_id))
        await update.message.reply_text("Команда выполнена")
    except:
        await update.message.reply_text("Не удалось выполнить команду")

@restricted
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count_apps = len(connect_mysql("SELECT * FROM applications WHERE status = 0"))
    count_reviews = len(connect_mysql("SELECT * FROM reviews WHERE status = 0"))
    keyboard = [[InlineKeyboardButton(text="Обращения (%s)" % count_apps,
                                        callback_data=str(APPLICATIONS))],
                [InlineKeyboardButton(text="Отзывы (%s)" % count_reviews,
                                        callback_data=str(REVIEWS))],
                [InlineKeyboardButton(text="Бонусы", callback_data=str(BONUSES))],
                [InlineKeyboardButton(text="Добавить менеджера",
                                        callback_data=str(ADD_ADMIN))],
                [InlineKeyboardButton(text="Удалить менеджера",
                                        callback_data=str(DEL_ADMIN))],
                [InlineKeyboardButton(text="Сообщение пользователям",
                                        callback_data=str(NEWSLETTER))],
                [InlineKeyboardButton(text="Промокоды",
                                        callback_data=str(PROMOCODES))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text=content.admin.MAINMENU, reply_markup=reply_markup)
    return ConversationHandler.END

# applications
@restricted
async def applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_data = context.user_data
    image = None
    pages = connect_mysql("SELECT * FROM applications;")

    # number это не индекс, а номер
    number = user_data.get("request page number", 1) 

    if query.data == str(LEFT): number -= 1
    elif query.data == str(RIGHT): number += 1

    if number < 1: number = 1
    if number > len(pages): number = len(pages)
    user_data["request page number"] = number

    left, callback_left = ('⬅️', LEFT) if number > 1 else ('⏹️', FALL)
    right, callback_right = ('➡️', RIGHT) if number < len(pages) else ('⏹️', FALL)

    keyboard = []
    if len(pages): 
        # здесь number минусуем, чтобы искать по индексу
        (id, user_id, message, image,
         contact, status) = (item for item in pages[number - 1])
        status = 'Ответ на заявку был' if status else 'Ответа на заявку не было'
        # Если изображения в бд нет, или если путь есть но не действителен:
        if not image:
            image = NOIMG
        elif not os.path.isfile(image):
            image = NODOWN
        
        text = (
            "Номер заявки: %s\n"
            "Текст заявки:\n\n"
            "%s\n\n"
            "Контакт: %s\n"
            "Статус: %s") % (id, message, contact, status)
        
        keyboard += [[InlineKeyboardButton(left, callback_data=str(callback_left)),
                    InlineKeyboardButton(right, callback_data=str(callback_right))],
                    [InlineKeyboardButton("Ответить",
                                      callback_data=str(ANSWER_APPLICATION) + '-' + str(id))],
                    [InlineKeyboardButton("Удалить",
                                      callback_data=str(DELETE_APPLICATION) + '-' + str(id))]]
    else: 
        text = "<Пусто>"
    
    reply_markup = InlineKeyboardMarkup(keyboard + back_menu)
    await construct_message(update, image=image,
                        text=text,
                        reply_markup=reply_markup)
    return APPLICATIONS

@restricted
async def answer_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_data = context.user_data
    id = (query.data).split('-')[-1] # id обращения/заявки
    user_data["application id"] = id
    reply_markup = InlineKeyboardMarkup(cancel)
    await construct_message(update, text=content.admin.APPLICATION_ANSWER,
                            reply_markup=reply_markup)
    return ANSWER_APPLICATION

@restricted
async def answer_application_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    text = update.effective_message.text
    user_data["application answer text"] = text
    keyboard = skip + cancel
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text=content.admin.IMAGE_OR_SKIP,
                            reply_markup=reply_markup)
    return APPLICATION_PREVIEW

@restricted
async def application_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_data["application answer image"] = image = await get_image(update, Paths.ANSWERS)
    text = user_data.get("application answer text", "Ошибка текста!")
    keyboard = [[InlineKeyboardButton("Отправить ответ",
                    callback_data=str(SEND_ANSWER))]] + cancel
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text=text, image=image)
    text = "Подтвердите отправку сообщения:"
    await update.effective_user.send_message(text=text,
                                             reply_markup=reply_markup)
    return APPLICATION_ANSWER_COMPLETE

@restricted
async def application_answer_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    id = user_data.get("application id")
    content.user.APPLICATION_ANSWER_COMPLETE % ('message')
    image = user_data.get("application answer image")
    text = user_data.get("application answer text")
    res = connect_mysql("SELECT * FROM applications WHERE id = %s", (id,))[0]
    chat_id = res[1]
    # Отправка сообщения пользователю
    text_to_admin = ""
    try:
        if not image:
            await context.bot.send_message(chat_id=chat_id, text=text)
        else:
            await context.bot.send_photo(chat_id=chat_id, caption=text,
                                        photo=image)
        text_to_admin += content.admin.APPLICATION_ANSWER_COMPLETE
        res = connect_mysql("UPDATE applications SET status = 1 WHERE id = %s;", (id, ))
        if not res:
            text_to_admin += "\n" + content.admin.MYSQL_ERROR
    except:
        text_to_admin = "\n" + content.admin.USER_LEAVE
    # Отправка результата менеджеру
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text=text_to_admin,
                            reply_markup=reply_markup)

    return ConversationHandler.END

@restricted
async def delete_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_data = context.user_data
    id = (query.data).split('-')[-1] # id обращения/заявки
    user_data["application id"] = id
    keyboard = list(update.effective_message.reply_markup.inline_keyboard)
    keyboard[-2] = [
        InlineKeyboardButton('Подтвердить',
                                callback_data=str(ACCEPT_DELETE_APPLICATION) + '-' + id),
        InlineKeyboardButton('Отмена',
                                callback_data=str(CANCEL_DELETE_APPLICATION))]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)
    return APPLICATIONS

@restricted
async def accept_delete_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    id = (query.data).split('-')[-1] # id обращения/заявки
    connect_mysql("DELETE FROM applications WHERE id = %s", (id,))
    await query.answer(text="Заявка удалена")
    return await applications(update, context)

@restricted
async def fall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()


# reviews
@restricted
async def reviews(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_data = context.user_data
    image = None
    pages = connect_mysql("SELECT * FROM reviews")

    # number это не индекс, а номер
    number = user_data.get("reviews page number", 1) 

    if query.data == str(LEFT): number -= 1
    elif query.data == str(RIGHT): number += 1

    if number < 1: number = 1
    if number > len(pages): number = len(pages)
    user_data["reviews page number"] = number

    left, callback_left = ('⬅️', LEFT) if number > 1 else ('⏹️', FALL)
    right, callback_right = ('➡️', RIGHT) if number < len(pages) else ('⏹️', FALL)

    keyboard = []
    if len(pages): 
        # здесь number минусуем, чтобы искать по индексу
        (id, user_id, image, status) = (item for item in pages[number - 1])
        
        confirm = [
            [InlineKeyboardButton("Подтвердить", callback_data=str(REVIEW_CONFIRM) + '-' + str(id))]
        ] if not status else [
            [InlineKeyboardButton("➖➖➖", callback_data=str(FALL))]
        ]
        
        status = 'Подтвержден' if status else 'Не подтвержден'

        if not image: image = NOIMG

        text = content.admin.REVIEWS % (id, status)
        
        keyboard += [[InlineKeyboardButton(left, callback_data=str(callback_left)),
                    InlineKeyboardButton(right, callback_data=str(callback_right))]]
        keyboard += confirm
        keyboard += [[InlineKeyboardButton("Удалить",
                                      callback_data=str(REVIEW_DELETE) + '-' + str(id))]]
    else: 
        text = "<Пусто>"
    
    reply_markup = InlineKeyboardMarkup(keyboard + back_menu)

    await construct_message(update, image=image,
                        text=text,
                        reply_markup=reply_markup)
    return REVIEWS

@restricted
async def review_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_data = context.user_data
    id = (query.data).split('-')[-1] # id обращения/заявки
    user_data["review id"] = id
    keyboard = list(update.effective_message.reply_markup.inline_keyboard)
    keyboard[-3] = [
        InlineKeyboardButton('Подтвердить',
                                callback_data=str(REVIEW_CONFIRM_ACCEPT) + '-' + id),
        InlineKeyboardButton('Отмена',
                                callback_data=str(REVIEW_CANCEL))]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)
    return REVIEWS

@restricted
async def review_confirm_accept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Данная функция работает как из админ-меню, так и из моментального админ-уведомления"""
    query = update.callback_query
    id = (query.data).split('-')[-1] # id обращения/заявки
    id, user_id, image, status = connect_mysql("SELECT * FROM reviews WHERE id = %s", (id,))[0]
    bonuses_score = connect_mysql("SELECT * FROM users WHERE user_id = %s", (user_id,))[0][3] # узнаем баланс пользователя
    connect_mysql("UPDATE reviews SET status = 1 WHERE id = %s", (id,)) # меняем статус заявки 
    bonuses = dict(connect_mysql("SELECT * FROM bonuses"))
    plus = bonuses.get(bonustype.REVIEW) # узнаем сколько должен получить пользователь
    bonuses_score += plus
    
    connect_mysql("UPDATE users SET bonuses = %s, lastmove = %s WHERE user_id = %s", (bonuses_score, now_time(), user_id)) # обновляем бонусный счет пользователю
    text = content.user.FEEDBACK_ACCEPT % plus
    # keyboard = [[InlineKeyboardButton("Отправить еще", callback_data=str(REVIEW))]] + user_menu
    # reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_photo(chat_id=user_id, caption=text,
                                 photo=image, ) # reply_markup=reply_markup
    text = "Отзыв #%s подтвержден\nПользователь уведомлен о полученных бонусах" % id
    if int(query.data.split('-')[0]) != REVIEW_CONFIRM_NOTIFICATION:
        await query.answer(text=text)
        # await update.effective_user.send_message(text=text)
        return await reviews(update, context)
    else:
        await construct_message(update, text=text, reply_markup=InlineKeyboardMarkup(back_menu))

@restricted
async def review_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_data = context.user_data
    id = (query.data).split('-')[-1] # id обращения/заявки
    user_data["review id"] = id
    keyboard = list(update.effective_message.reply_markup.inline_keyboard)
    keyboard[-2] = [
        InlineKeyboardButton('Подтвердить',
                                callback_data=str(REVIEW_DELETE_ACCEPT) + '-' + id),
        InlineKeyboardButton('Отмена',
                                callback_data=str(REVIEW_CANCEL))]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)
    return REVIEWS

@restricted
async def review_accept_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    id = (query.data).split('-')[-1] # id обращения/заявки
    connect_mysql("DELETE FROM reviews WHERE id = %s", (id,))
    await query.answer(text="Отзыв удален")
    return await reviews(update, context)


# bonuses
@restricted
async def bonus_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bonuses = connect_mysql("SELECT * FROM bonuses")
    keyboard = [[InlineKeyboardButton("Изменить", callback_data=str(CHANGE_BONUSES))]] + back_menu
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = ""
    for row in bonuses:
        text += f"{row[0]}: {row[1]}\n"
    text = content.admin.BONUS_INFO % text
    await construct_message(update, text=text,
                            reply_markup=reply_markup)
    return CHANGE_BONUSES

@restricted
async def change_bonuses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = content.admin.CHANGE_BONUSES
    bonuses = connect_mysql("SELECT * FROM bonuses")
    keyboard = []
    for row in bonuses:
        keyboard.append([InlineKeyboardButton(f"{row[0]}: {row[1]}",
                            callback_data=f"{CHOOSE_BONUS}-{row[0]}")])
    keyboard += back_menu
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text, reply_markup=reply_markup)
    return ENTER_BONUS_VALUE

@restricted
async def enter_bonus_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bonus_type = (update.callback_query.data).split("-")[-1]
    text = content.admin.ENTER_BONUS_VALUE % bonus_type
    context.user_data["bonus type"] = bonus_type
    keyboard = cancel + back_menu
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text, reply_markup)
    return CHANGED_BONUS_VALUE

@restricted
async def changed_bonus_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    value = update.effective_message.text
    bonus_type = context.user_data["bonus type"]
    if not value.isdigit():
        # await update.effective_user.send_message("Некорректный ввод")
        await construct_message(update, "Некорректный ввод.\nПопробуйте еще раз.")
        return CHANGED_BONUS_VALUE
    res = connect_mysql("UPDATE bonuses SET value = %s WHERE type = %s", (value, bonus_type))
    if not res:
        await update.effective_user.send_message(content.admin.MYSQL_ERROR)
        return ConversationHandler.END
    text = content.admin.CHANGED_BONUS_VALUE % (bonus_type, value)
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return ConversationHandler.END


# add admin
@restricted
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admins = connect_mysql("SELECT * FROM managers")
    if admins:
        admins = '\n'.join([str(x[0]) for x in admins])
    else:
        admins = "<пусто>"
    text = content.admin.ENTER_USERID % admins
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return WAIT_ID

@restricted
async def admin_added(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_message.text
    if not user_id.isdigit():
        await update.effective_user.send_message(
            "Некорректный ввод.\nПопробуйте снова:"
        )
        return WAIT_ID
    res = connect_mysql("INSERT INTO managers (user_id) VALUES (%s)", (user_id,))
    if not res:
        await update.effective_user.send_message(content.admin.MYSQL_ERROR)
        return ConversationHandler.END
    text = content.admin.MANAGER_ADDED % user_id
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return ConversationHandler.END


# del admin
@restricted
async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admins = connect_mysql("SELECT * FROM managers")
    if admins:
        admins = '\n'.join([str(x[0]) for x in admins])
    else:
        admins = "<пусто>"
    text = content.admin.ENTER_USERID % admins
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return WAIT_ID

@restricted
async def admin_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_message.text
    if not user_id.isdigit():
        await update.effective_user.send_message(
            "Некорректный ввод.\nПопробуйте снова:"
        )
        return WAIT_ID
    res = connect_mysql("DELETE FROM managers WHERE user_id = %s", (user_id,))
    if not res:
        await update.effective_user.send_message(content.admin.MYSQL_ERROR)
        return ConversationHandler.END
    text = content.admin.MANAGER_DELETED % user_id
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return ConversationHandler.END


# newsletter
@restricted
async def newsletter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    await update.callback_query.answer()
    user_data['button for users'] = False
    text = content.admin.ENTER_MESSAGE_TEXT
    reply_markup = InlineKeyboardMarkup(cancel)
    await construct_message(update, text, reply_markup)
    return MSG_FOR_USERS_STATE

@restricted
async def newsletter_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_data['message for users'] = update.message.text
    text = content.admin.IMAGE_OR_SKIP
    keyboard = [[InlineKeyboardButton('Пропустить', callback_data=str(SKIP))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=text, reply_markup=reply_markup)
    return PHOTO_STATE

@restricted
async def newsletter_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    text = content.admin.BUTTON_OR_SKIP
    keyboard = [[InlineKeyboardButton('Да', callback_data=str(YES))],
                [InlineKeyboardButton('Нет', callback_data=str(NO))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    user_data['photo for users'] = await get_image(update, Paths.NEWSLETTERS)
    await construct_message(update, text, reply_markup)

    return BUTTON_FOR_USERS

@restricted
async def button_or_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    query = update.callback_query
    replpy_markup = InlineKeyboardMarkup(cancel)
    if query.data == str(NO):
        user_data['button for users'] = False
        await newsletter_preview(update, context)
    else:
        user_data['button for users'] = True
        text = content.admin.BUTTON_TEXT
        await construct_message(update, text=text, reply_markup=replpy_markup)
        return TEXT_FOR_USERS_BTN

@restricted
async def button_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_data['text for users btn'] = update.message.text
    text = content.admin.BUTTON_LINK
    replpy_markup = InlineKeyboardMarkup(cancel)
    await update.message.reply_text(text=text, reply_markup=replpy_markup)
    return LINK_FOR_USERS_BTN

@restricted
async def newsletter_preview(update: Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    keyboard_user = []

    if user_data['button for users']:
        url = update.message.text
        text_btn = user_data['text for users btn']
        keyboard_user.append([InlineKeyboardButton(text_btn, url=url)])
    user_data['keyboard for user message'] = keyboard_user

    keyboard = [[InlineKeyboardButton('Отправить',
                    callback_data=str(SEND_USER_MSG))]] + cancel
    reply_markup = InlineKeyboardMarkup(keyboard_user) 
    text = user_data['message for users']
    try:
        await construct_message(update, text, reply_markup,
                                image=user_data['photo for users'])
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "Подтвердите рассылку всем пользователям:"
        await update.effective_user.send_message(text=text,
                                        reply_markup=reply_markup)
    except error.BadRequest as err: # telegram.error.BadRequest
        text = "Ошибка."
        if 'url' in str(err):
            text = "Ошибка.\nПроверьте корректность ссылки."
        reply_markup = InlineKeyboardMarkup(back_menu)
        await update.message.reply_text(text=text, reply_markup=reply_markup)
        return ConversationHandler.END
    return SEND_MESSAGE_USERS

@restricted
async def newsletter_complete(update: Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    # Находим в базе данных всех пользователей
    result = connect_mysql("SELECT * FROM users")
    text = user_data['message for users']
    keyboard = user_data['keyboard for user message']
    reply_markup = InlineKeyboardMarkup(keyboard)
    photo = user_data['photo for users']
    if photo:
        for user in result:
            try: await context.bot.send_photo(chat_id=user[0], photo=photo,
                                            caption=text, reply_markup=reply_markup)
            except: pass # Если пользователя больше нет в боте
    else:
        for user in result:
            try: await context.bot.send_message(chat_id=user[0], 
                                        text=text, reply_markup=reply_markup)
            except: pass # Если пользователя больше нет в боте

    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, content.admin.NEWSLETTER_SENT,
                                    reply_markup=reply_markup)
    return ConversationHandler.END


# promocodes
def set_promocodes(promocodes_path: list):
    """
    Загрузка промокодов из таблицы xlsx в базу данных.
    Возвращает результат mysql запроса.
    """
    sheets = read_excel(promocodes_path, sheet_name=None)
    for sheet_name, sheet in sheets.items():
        break
    promocodes = dict(sheet.values.tolist())
    qr = "INSERT INTO promocodes (code, status) VALUES"
    for row in promocodes.items():
        qr += " ('%s', %s)," % tuple(row)
    qr = qr[:-1] + ";"
    return connect_mysql(qr)

def get_promocodes() -> str:
    """
    Подтягиваем из базы данных таблицу с промокодами 
    и сразу преобразовываем данные в xlsx.
    Возвращается путь до xlsx файла
    """
    promocodes = connect_mysql("SELECT * FROM promocodes")
    wb = Workbook() # создание новой книги
    sheet = wb.active # получение активного листа
    if promocodes:
        sheet.append(["Промокод", "Статус"])
        for data in promocodes:
            sheet.append(data) # data = [str, int] -> [code, status]
    promocodes_path = Paths.FILES + "/promocodes.xlsx"
    wb.save(promocodes_path)
    return promocodes_path

@restricted
async def promocodes(update: Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    text = content.admin.PROMOCODES
    keyboard = [[InlineKeyboardButton("Обновить промокоды",
                    callback_data=str(UPDATE_PROMOCODES))],
                [InlineKeyboardButton("Выгрузить промокоды",
                    callback_data=str(DOWNLOAD_PROMOCODES))]] + back_menu
    reply_markup = InlineKeyboardMarkup(keyboard)
    await construct_message(update, text, reply_markup)
    return PROMOCODES

@restricted
async def update_promocodes(update: Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    text = content.admin.UPDATE_PROMOCODES
    reply_markup = InlineKeyboardMarkup(cancel)
    await construct_message(update, text, reply_markup)
    return UPDATE_PROMOCODES

@restricted
async def update_promocodes_complete(update: Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    '''получаем документ xlsx'''
    document = await update.message.document.get_file()
    file_name = update.message.document.file_name
    file_name = rename_file(file_name, Paths.PROMOCODES)
    document_path = rf'{Paths.PROMOCODES}/{file_name}'
    await document.download_to_drive(document_path)
    # для безопасности сохраняем старые промокоды
    promocodes_old = get_promocodes() 
    try:
        # перезаписываем таблицу промокодов:
        connect_mysql("DELETE FROM promocodes")
        result = set_promocodes(document_path)
        assert result
        text = content.admin.UPDATE_PROMOCODES_COMPLETE
    except:
        text = "Ошибка при загрузке новых промокодов.\nПроверьте таблицу и попробуйте снова"
        # удаленные промокоды обратно возвращаем в базу данных
        result = set_promocodes(promocodes_old)
    
    reply_markup = InlineKeyboardMarkup(back_menu)
    await construct_message(update, text, reply_markup)
    return ConversationHandler.END

@restricted
async def download_promocodes(update: Update,context:ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = InlineKeyboardMarkup(back_menu)
    promocodes_path = get_promocodes()
    if promocodes_path:
        text = content.admin.DOWNLOAD_PROMOCODES
        await update.callback_query.answer()
        await update.effective_user.send_document(document=promocodes_path,
                                                caption=text,
                                                reply_markup=reply_markup)
        # await update.callback_query.delete_message() # почему-то не удаляется сообщение
    else:
        text = "Возникла ошибка при выгрузке промокодов из базы данных"
        await construct_message(update, text, reply_markup)

    return ConversationHandler.END


# other
@restricted
async def cancel_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reply_markup = InlineKeyboardMarkup(back_menu)
    text = "Операция отменена"
    await construct_message(update, text=text, reply_markup=reply_markup)
    return ConversationHandler.END


# fallbacks
from user import start # данный импорт нужен именно здесь
fallbacks = [CallbackQueryHandler(admin, pattern=f"^{ADMIN_MENU}$"),
               CallbackQueryHandler(start, pattern=f"^{USER_MENU}$"),
               CallbackQueryHandler(cancel_message, pattern=f"^{CANCEL}$"),
               CommandHandler("admin", admin),
               CommandHandler("start", start)]


# Conversations
conv_applications = ConversationHandler(
    entry_points=[CallbackQueryHandler(applications,
                                       pattern=f"^{APPLICATIONS}$")],
    states={
        APPLICATIONS: 
        [CallbackQueryHandler(applications,
            pattern=f"^{LEFT}$|^{RIGHT}$|^{CANCEL_DELETE_APPLICATION}$"),
        CallbackQueryHandler(answer_application,
                            pattern=f"^({ANSWER_APPLICATION}-)"), 
        CallbackQueryHandler(delete_application,
                            pattern=f"^({DELETE_APPLICATION}-)"),
        CallbackQueryHandler(accept_delete_application,
                            pattern=f"^({ACCEPT_DELETE_APPLICATION}-)"), 
        CallbackQueryHandler(fall,
                            pattern=f"^{FALL}$")],
        ANSWER_APPLICATION:
        [MessageHandler(filters.TEXT & ~filters.COMMAND,
                            answer_application_image)],
        APPLICATION_PREVIEW:
        [MessageHandler(filters.PHOTO | filters.Document.IMAGE,
                        application_preview),
        CallbackQueryHandler(application_preview,
                             pattern=f"^{SKIP}$")],
        APPLICATION_ANSWER_COMPLETE:
        [CallbackQueryHandler(application_answer_complete,
                              pattern=f"^{SEND_ANSWER}$")]
        
    },  
    fallbacks=fallbacks
)

conv_reviews = ConversationHandler(
    entry_points=[CallbackQueryHandler(reviews,
                                       pattern=f"^{REVIEWS}$")],
    states={
        REVIEWS: 
        [CallbackQueryHandler(reviews,
            pattern=f"^{LEFT}$|^{RIGHT}$|^{REVIEW_CANCEL}$"),
        CallbackQueryHandler(review_confirm,
                            pattern=f"^({REVIEW_CONFIRM}-)"), 
        CallbackQueryHandler(review_confirm_accept,
                            pattern=f"^({REVIEW_CONFIRM_ACCEPT}-)"),
        CallbackQueryHandler(review_delete,
                            pattern=f"^({REVIEW_DELETE}-)"),
        CallbackQueryHandler(review_accept_delete,
                            pattern=f"^({REVIEW_DELETE_ACCEPT}-)"), 
        CallbackQueryHandler(fall,
                            pattern=f"^{FALL}$")]    
    },  
    fallbacks=fallbacks
)

conv_bonuses = ConversationHandler(
    entry_points=[CallbackQueryHandler(bonus_info,
                    pattern=f"^{BONUSES}$")],
    states={
        CHANGE_BONUSES:
            [CallbackQueryHandler(change_bonuses,
                    pattern=f"^{CHANGE_BONUSES}$")],
        ENTER_BONUS_VALUE:
            [CallbackQueryHandler(enter_bonus_value,
                    pattern=f"^({CHOOSE_BONUS}-)")],
        CHANGED_BONUS_VALUE:
            [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                        changed_bonus_value)]
    },
    fallbacks=fallbacks
)

conv_add_admin = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_admin,
                    pattern=f"^{ADD_ADMIN}$")],
    states={
        WAIT_ID:
            [MessageHandler(filters.TEXT & ~filters.COMMAND,
                            admin_added)]
    },
    fallbacks=fallbacks
)

conv_del_admin = ConversationHandler(
    entry_points=[CallbackQueryHandler(del_admin,
                    pattern=f"^{DEL_ADMIN}$")],
    states={
        WAIT_ID:
            [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                admin_deleted)]
    },
    fallbacks=fallbacks
)

conv_newsletter = ConversationHandler(
    entry_points=[CallbackQueryHandler(newsletter, pattern=f"^{NEWSLETTER}$")],
    states={
        MSG_FOR_USERS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                        newsletter_image)],
        PHOTO_STATE: [MessageHandler(filters.PHOTO | filters.Document.IMAGE,
                                        newsletter_button),
                    CallbackQueryHandler(newsletter_button,
                                            pattern=f"^{SKIP}$")],
        BUTTON_FOR_USERS: [CallbackQueryHandler(button_or_skip,
                                            pattern=f"^{YES}$"),
                        CallbackQueryHandler(newsletter_preview,
                                            pattern=f"^{NO}$")],
        TEXT_FOR_USERS_BTN: [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                        button_link)],
        LINK_FOR_USERS_BTN: [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                        newsletter_preview)],
        SEND_MESSAGE_USERS: [CallbackQueryHandler(newsletter_complete,
                                            pattern=f"^{SEND_USER_MSG}$")],
        FALL: [],
    },
    fallbacks=fallbacks
)

conv_promocodes = ConversationHandler(
    entry_points=[CallbackQueryHandler(promocodes, pattern=f"^{PROMOCODES}$")],
    states={
        PROMOCODES: [CallbackQueryHandler(update_promocodes, pattern=f"^{UPDATE_PROMOCODES}$"),
                     CallbackQueryHandler(download_promocodes, pattern=f"^{DOWNLOAD_PROMOCODES}$")],
        UPDATE_PROMOCODES: [MessageHandler(filters.Document.ALL, update_promocodes_complete)],
        FALL: [],
    },
    fallbacks=fallbacks
)