from fastapi import FastAPI
import uvicorn
import os
from pydantic import BaseModel
import requests
# import ssl
from fastapi.middleware.cors import CORSMiddleware
import json
from validate import validate_init_data
from dbconnect import Mysql
import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
from dotenv import load_dotenv
load_dotenv()

USER_MENU = 1
TOKEN = os.getenv('TOKEN_LOVIX')
USER = os.getenv('user_lovix_db')
PASS = os.getenv('pass_lovix_db')
HOST = os.getenv('host_lovix_db')
DATABASE = os.getenv('database_lovix_db')

app = FastAPI()
connect_mysql = Mysql(USER, PASS, HOST, DATABASE)

keyfile = "/etc/letsencrypt/live/lovixbot.duckdns.org/privkey.pem"
sertfile = "/etc/letsencrypt/live/lovixbot.duckdns.org/fullchain.pem"
host = "lovixbot.duckdns.org"
# uvicorn main:app --ssl-keyfile /etc/letsencrypt/live/webe.duckdns.org/privkey.pem --ssl-certfile /etc/letsencrypt/live/webe.duckdns.org/fullchain.pem --host webe.duckdns.org --port 8000

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain('/etc/letsencrypt/live/webe.duckdns.org/fullchain.pem',
#                             keyfile='/etc/letsencrypt/live/webe.duckdns.org/privkey.pem')

# из каких мест будут приниматься и обрабатываться запросы
origins = ["https://lovixbot.duckdns.org"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Product(BaseModel):
    init_data: str
    image: str
    title: str
    bonuses: int
    description: str
    tag: str


@app.post("/product/")
def send_product(product: Product):
    valid_data = validate_init_data(product.init_data, TOKEN)
    # logging.info(valid_data)

    if not valid_data: return 404

    chat_id = json.loads(valid_data.get("user")).get("id")

    row = connect_mysql("SELECT * FROM users WHERE user_id = %s", (chat_id,))
    print('row', row)
    if not row: return 404
    user_bonuses = row[0][3]

    # https://core.telegram.org/bots/api#sendphoto
    method = "sendPhoto" 

    text = f"{product.title}\n" \
            f"Стоимость {product.bonuses} бонусов\n" \
             f"{product.description}"

    if user_bonuses >= product.bonuses:
        btn_txt = "Получить за %s бонусов" % product.bonuses
        keyboard = [[{"text": btn_txt,
                      "callback_data": f"exchange-{product.title}" \
                        f"-{product.bonuses}-{product.tag}"}]]
    else:
        keyboard = [[{"text": "Нехватает бонусов", "callback_data": "999"}]]
    keyboard += [[{"text": "В главное меню", "callback_data": str(USER_MENU)}]]
    reply_markup = {"inline_keyboard": keyboard}
    reply_markup = json.dumps(reply_markup)

    response = requests.post(
            url=f'https://api.telegram.org/bot{TOKEN}/{method}',
            data={'chat_id': chat_id,
                  'photo': product.image,
                  'caption': text,
                  "reply_markup": reply_markup}
        ).json()
    
    # print('response', response)

if __name__ == "__main__":
    uvicorn.run("main:app", host=host, port=8000,
                    ssl_keyfile=keyfile, ssl_certfile=sertfile)