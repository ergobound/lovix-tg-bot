from dotenv import load_dotenv
import os
load_dotenv()

TOKEN = os.getenv('TOKEN_LOVIX')
BOT_NAME = 'nexterrorbot' # lovixbot
CHANNEL_ID = -1001897814685 # -1002006611158
CHANNEL_LINK = "t.me/nexterror" # "t.me/lovix_me"
CHANNEL_NAME = "nexterror"
# WEBURL = "https://webe.duckdns.org"
WEBURL = "https://lovixbot.duckdns.org"
ADMINS = [479917441]
DEVELOPER = 479917441

class db:
    USER = os.getenv('user_lovix_db')
    PASS = os.getenv('pass_lovix_db')
    HOST = os.getenv('host_lovix_db')
    DATABASE = os.getenv('database_lovix_db')

class Paths:
    '''Пути до папок, где будут хранится файлы'''
    ANSWERS = "images/answers"
    APPLICATIONS = "images/applications"
    NEWSLETTERS = "images/newsletters"
    CHECKS = "checks"
    EXTRACT = "checks/extract"
    REVIEWS = "images/reviews"

    FILES = "files"
    PROMOCODES = "files/promocodes"

    ALL = [ANSWERS, APPLICATIONS, NEWSLETTERS,
           CHECKS, EXTRACT, REVIEWS, PROMOCODES]

class bonustype:
    WELCOME = "Приветственные"
    FOLLOW = "Подписка на канал"
    CHECK = "Регистрация чека"
    REVIEW = "Отзыв"
    INVITE = "Пригласить друга"

# Подарки должны быть в том же порядке, что и базе данных purchased_gifts
# А так же ключи должен совпадать со названиями столбцов в purchased_gifts
GIFTS_INFO = {
    "sticker_pack": ["Стикер-пак", 300],
    "lubricant": ["Набор лубрикантов", 450],
    "box": ["Бокс", 700],
    "merch": ["Мерч", 900],
    "webinar": ["Вебинар от Сикрет Центра", 1200]
}

NOIMG = "images/no-image.jpg"
ERR = "images/err.png"
NODOWN = "images/no-down-image.png"
PLUG = "images/plug.png"

ADMIN_MENU, USER_MENU = 0, 1

(
# ADMIN
# menu
APPLICATIONS,
REVIEWS,
BONUSES,
ADD_MANAGER,
DEL_MANAGER,
NEWSLETTER,
PROMOCODES,
# applications
ANSWER_APPLICATION,
DELETE_APPLICATION,
ACCEPT_DELETE_APPLICATION,
CANCEL_DELETE_APPLICATION,

APPLICATION_PREVIEW,
APPLICATION_ANSWER_COMPLETE,
SEND_ANSWER,

# reviews
REVIEW_CONFIRM,
REVIEW_CONFIRM_ACCEPT,
REVIEW_DELETE,
REVIEW_DELETE_ACCEPT,
REVIEW_CANCEL,

# bonuses
CHANGE_BONUSES,
CHOOSE_BONUS,
ENTER_BONUS_VALUE,
CHANGED_BONUS_VALUE,

# manager add / del
ADD_ADMIN,
DEL_ADMIN,
WAIT_ID,

# newsletter
MESSAGE_FOR_USERS,
MSG_FOR_USERS_STATE,
PHOTO_STATE,
BUTTON_FOR_USERS,
TEXT_FOR_USERS_BTN,
LINK_FOR_USERS_BTN,
SEND_MESSAGE_USERS,
SEND_USER_MSG,

# promocodes
UPDATE_PROMOCODES,
UPDATE_PROMOCODES_COMPLETE,
DOWNLOAD_PROMOCODES,


# USER
# start
CONSENT,
SHARE_PHONE,
REJECTED,
COMEBACK,
RAFFLE,
RAFFLE_ENTRY, # TAKE_PART
YES_CONSENT,
NO_CONSENT,


# menu
SOLO_TEST,
GET_BONUSES,
GIFTS,
SUPPORT,
# solo test
TEST_PREVIEW,
TAKE_TEST,
PROCESS_TEST,
TEST_FINAL,
# bonus menu
CHECK,
REVIEW,
FOLLOW,
REFERRAL,

WAIT_CHECK,

WAIT_REVIEW,
# gifts

# support
SUPPORT_IMG,
SUPPORT_CONTACT,
SEND_CONTACT,
SEND_APPLICATION,
APPLICATION_COMPLETE,

EMAIL, PHONE,
TELEGRAM,

# other
REVIEW_CONFIRM_NOTIFICATION,
LEFT, RIGHT, FALL,
YES, NO,
CANCEL,
SKIP) = range(2, 77)

LETTERS = ["A", "B",
           "C", "D",
           "E", "F",
           "G", "H",
           "I", "J",
           "K", "L"]