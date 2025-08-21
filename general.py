from telegram import (
    Update,
    InputMediaPhoto,
    ChatMemberUpdated, #
    Message
)
from telegram.ext import (
    ContextTypes
)
from typing import Optional # 
from telegram.constants import ParseMode
from random import randint
from constants import *
import mysql.connector
from functools import wraps
import datetime
from pyzbar.pyzbar import decode # pyzbar
from PIL import Image
import json
import html
import traceback
import io
import os
import fitz  # PyMuPDF
import content

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
import logging, sys
filterwarnings(action="ignore",
               message=r".*CallbackQueryHandler",
               category=PTBUserWarning)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

class Mysql:
    '''Подключение к базе данных'''

    def __init__(self, user, password, host, database):
        self.connection = mysql.connector.connect(user=user,
                                            password=password,
                                            host=host,
                                            database=database)

    def __call__(self, query, data=None):
        try:
            result = None
            # if not connection.is_connected():
            #     connection = mysql.connector.connect(user=user, password=password,
            #                                             host=host, database=database)
            self.connection.reconnect()

            cursor = self.connection.cursor()
            try:
                cursor.execute(query, data)
            except mysql.connector.errors.IntegrityError as err:
                print('Один из элементов является дубликатом.\n' + err.msg)
                # return mysql.connector.errors.IntegrityError
                return None
            except mysql.connector.errors.DataError as err:
                print(err, err.msg)
                # return 'Слишком большое количество символов.'
                return None
            if cursor.description is None:
                self.connection.commit()
                print(cursor)         
                result = {'lastrowid': cursor.lastrowid, # получить id последнего добавленного
                        'rowcount': cursor.rowcount}  # получить количество удаленных/добавленных строк
            else:
                result = list(cursor)
            try:
                cursor.close()
                self.connection.close()
            except mysql.connector.errors.InternalError:
                # return 'Обнаружен непрочитанный результат.'
                return None
            return result
            
        except BaseException as err:
            # logging.info('Глобальная ошибка: ' + str(err))
            print('Глобальная ошибка: ' + str(err))
            # return 'Произошла ошибка в функции mysql_query. Обратитесь к создателю телеграм бота!'
            return None

def open_path(paths: list):
    """Создает пути, если их нет
    Args:
        paths (list) :
            example: ["home/folder", "/home/folder/"]"""
    for path in paths:
        parts = path.split("/")
        snake_path = []
        for part in parts:
            if part:
                snake_path.append(part)
                p = "/".join(snake_path)
                if not os.path.exists(p):
                    os.mkdir(p)

open_path(Paths.ALL)

def now_time() -> str:
    now = datetime.datetime.now()
    now = datetime.datetime.strftime(now, "%Y.%m.%d - %H:%M:%S")
    return now

def technical_moment(func):
    @wraps(func)
    async def wrapped(update: Update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMINS:
            await update.effective_message.reply_text('Идут технические работы.')
            # logging.info(f"Неавторизованный доступ запрещен для {user_id}.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

def extract_images_from_pdf(pdf_path, output_dir):
    """
    Извлекает все изображения из PDF-файла,
    сохраняет их в указанный каталог и возвращает пути файлов.

    Args:
        pdf_path (str): Путь к PDF-файлу.
        output_dir (str): Путь к каталогу для сохранения извлеченных изображений.

    Returns:
        list: Возвращает список путей вытянутых изображений
    """
    try:
        doc = fitz.open(pdf_path)
        extract_images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            image_list = page.get_images()

            if image_list:
                print(f"На странице {page_num + 1} найдено {len(image_list)} изображений.")
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Преобразование CMYK в RGB, если необходимо
                    if base_image["colorspace"] == fitz.csCMYK:
                         import PIL.Image
                         image = PIL.Image.open(io.BytesIO(image_bytes))
                         image = image.convert("RGB")
                         image_bytes = io.BytesIO()
                         image.save(image_bytes, format="PNG")
                         image_bytes = image_bytes.getvalue()
                         image_ext = "png" # Изменяем расширение на png

                    filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    filename = rename_file(filename, output_dir)
                    image_path = f"{output_dir}/{filename}"
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    print(f"Изображение сохранено: {image_path}")
                    extract_images.append(image_path)
        doc.close()
        return extract_images
    except Exception as e:
        print(f"Ошибка при обработке PDF: {e}")

def find_qr_in_image(image_path) -> list | None:
    """
    Находит QR-коды в изображении.
    Args:
        image_path: Путь к изображению.
    Returns:
        Список расшифрованных данных QR-кодов.
    """
    try:
        img = Image.open(image_path)
        decoded_objects = decode(img)
        results = []
        for obj in decoded_objects:
            # Декодируем данные в строку
            results.append(obj.data.decode('utf-8')) 
        return results
    except:
        return 
    # except FileNotFoundError:
    #     return f"Ошибка: Файл не найден по пути {image_path}"
    # except Exception as e:
    #     return f"Ошибка при обработке изображения: {e}"

def rename_file(file_name: str, path: str) -> str: 
    '''Изменение имени файла в двух этапах.
    Первый этап: нахождение дубликата по указанному пути,
    и если дубликат найдет, то к новому файлу добавляется рандомный символ.
    Второй этап: на всякий случай фильтрует символы, убирая "неизвестные",
    символы.
    
    Args:
        file_name (str): имя файла
        path (str): путь куда предполагается положить файл

    Returns:
        str: Возвращает название файла (Не полный путь!)    '''
    
    # 1
    result = os.walk(path)
    files = []
    for adrs, dirs, fls in result:
        files.extend(fls)
    while file_name in files:
        lst_file = file_name.split('.')
        file_name = lst_file[0] + '-' + chr(randint(97,122)) + "." + lst_file[1]
    # 2
    file_name_new = ''
    for letter in file_name:
        if (letter >= 'A' and letter <= 'z' or
            letter >= 'А' and letter <= 'я' or
            letter == '.' or letter == ' ' or
            letter == '-' or letter == '_' or
            letter >= '0' and letter <= '9'):
            file_name_new += letter
    return file_name_new


async def get_image(update: Update, path: str) -> str | None:
    '''Скачивание файла.
    Возвращает путь до скаченного файла или None.
    update - обязательно;
    path - это путь куда нужно скачать файл'''
    message = update.to_dict().get('message')
    if not message: return
    if message.get('photo'):
        photo_file = await update.message.photo[-1].get_file()
        file_name = rf'{photo_file.file_unique_id}.jpg'
        file_name = rename_file(file_name, path)
        photo_path = rf'{path}/{file_name}'
        await photo_file.download_to_drive(photo_path)
        return photo_path
    elif message.get('document'):
        if "image" not in update.message.document.mime_type: return
        photo_file = await update.message.document.get_file()
        file_name = update.message.document.file_name
        file_name = rename_file(file_name, path)
        photo_path = rf'{path}/{file_name}'
        await photo_file.download_to_drive(photo_path)
        return photo_path
    return None

async def get_pdf(update: Update, path: str) -> str | None:
    '''Скачивание pdf файла в путь path'''
    message = update.to_dict().get('message')
    if not message: return
    if not message.get("document"): return
    if update.message.document.mime_type != 'application/pdf': return
    pdf_file = await update.message.document.get_file()
    file_name = update.message.document.file_name
    file_name = rename_file(file_name, path)
    pdf_path = rf'{path}/{file_name}'
    await pdf_file.download_to_drive(pdf_path)
    return pdf_path

async def construct_message(update: Update, text=None, reply_markup=None,
                            image=None, parse_mode=None) -> Message:
    '''Эта функция для упрощения отправки нового сообщения или изменения старого.
    Не стоит забывать, что всегда нужно прикреплять update'''

    # Можно добавить проверку на время.
    # Создать константу где будет хранится время запуска бота,
    # а здесь проверять сообщение с кнопкой было создано до запуска или после,
    # если первое, то изменять сообщение аля "кнопка устарела..."
    query = update.callback_query
    prev_message = update.effective_message.to_dict()
    if prev_message.get("photo"):
        if query: # data.get("callback_query")
            await query.answer()
            if image: # or media
                # изменяем сообщение по нажатию кнопки, прикрепляем фото
                media = InputMediaPhoto(media=open(image, 'rb'),
                                        caption=text, parse_mode=parse_mode)
                message = await query.edit_message_media(media=media, reply_markup=reply_markup)     
            else:
                # отправляем сообщение без фото
                message = await update.effective_message.reply_text(
                                    text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                # удаляем предыдущий message
                try: await query.delete_message()
                except: pass
        else:
            if image: # or media
                # отправляем сообщение с фоткой или медиа
                message = await update.effective_message.reply_photo(photo=image,
                        caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                # отправляем сообщение без фото
                message = await update.effective_message.reply_text(
                        text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif prev_message.get("document"):
        if query: await query.answer()
        if image: # or media
            # отправляем сообщение с фоткой или медиа
            message = await update.effective_message.reply_photo(photo=image,
                    caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            # отправляем сообщение без фото
            message = await update.effective_message.reply_text(
                    text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        if query: # data.get("callback_query")
            await query.answer()
            if image: # or media
                # отправляем новое сообщение, прикрепляем фото
                message = await update.effective_message.reply_photo(photo=image,
                        caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                # message = await update.effective_user.send_photo(
                #     photo=image, caption=text,
                #         reply_markup=reply_markup, parse_mode=parse_mode)
                # удаляем предыдущее сообщение
                try: await query.delete_message()
                except: pass
            else:
                # изменяем сообщение, без медиа
                message = await query.edit_message_text(text=text,
                            reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            if image: # or media
                # отправляем сообщение с фоткой или медиа
                message = await update.effective_message.reply_photo(photo=image,
                        caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            else:
                # отправляем сообщение без фото
                message = await update.effective_message.reply_text(
                        text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    return message

async def periodic_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    connect_mysql = Mysql(db.USER, db.PASS, db.HOST, db.DATABASE)
    users = connect_mysql("SELECT * FROM users")
    for user in users:
        user_id, bonuses = user[0], user[3]
        try:
            text = content.user.PERIODIC_NOTIFICATION % bonuses
            await context.bot.send_message(chat_id=user_id, text=text)
        except:
            pass

async def bonuses_burn_out(context: ContextTypes.DEFAULT_TYPE) -> None:
    connect_mysql = Mysql(db.USER, db.PASS, db.HOST, db.DATABASE)
    users = connect_mysql("SELECT * FROM users WHERE bonuses > 0")
    two_month = datetime.timedelta(days=62)
    now = datetime.datetime.now()
    for user in users:
        t = datetime.datetime.strptime(user[4], "%Y.%m.%d - %H:%M:%S")
        if t + two_month < now:
            connect_mysql("UPDATE users SET bonuses = 0 WHERE user_id = %s", (user[0],))


async def post_init(context: ContextTypes.DEFAULT_TYPE) -> None:
    print('post init')
    two_week = datetime.timedelta(days=14)
    every_day = datetime.timedelta(days=1)
    context.job_queue.run_repeating(bonuses_burn_out, interval=every_day)
    context.job_queue.run_repeating(periodic_notifications, interval=two_week)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "При обработке update возникла ошибка: \n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.bot_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await context.bot.send_message(
        chat_id=DEVELOPER, text=message, parse_mode=ParseMode.HTML
    )

async def handle_invalid_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    text = "Ошибка"
    try:
        await update.effective_message.edit_text(text=text)
    except:
        photo = 'images/err.png'
        media = InputMediaPhoto(media=open(photo, 'rb'), caption=text)
        await update.effective_message.edit_media(media=media)

async def everything_else(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "Возникла странность.\nПопробуйте снова /start"
    await construct_message(update, text=text)