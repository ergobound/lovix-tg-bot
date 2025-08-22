import hmac
import hashlib
from urllib.parse import parse_qsl, urlencode
import os

def validate_init_data(init_data: str, bot_token: str) -> bool:
    """
    Проверяет валидность данных из Telegram Mini App.
    
    :param init_data: Строка с параметрами (например, из window.Telegram.WebApp.initData)
    :param bot_token: Секретный токен вашего бота (например, '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')
    :return: True если данные валидны, иначе False
    """
    # Парсим строку параметров
    parsed_data = parse_qsl(init_data, keep_blank_values=True)
    
    # Извлекаем значение hash и фильтруем остальные параметры
    received_hash = None
    data_pairs = []
    for key, value in parsed_data:
        if key == 'hash':
            received_hash = value
        else:
            data_pairs.append((key, value))
    
    if not received_hash:
        return False  # Параметр hash отсутствует
    # Сортируем параметры в лексикографическом порядке
    data_pairs.sort(key=lambda x: x[0])
    
    # Формируем data-check-string
    data_check_string = "\n".join(
        [f"{key}={value}" for key, value in data_pairs]
    )
    
    # Генерируем секретный ключ
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256
    ).digest()
    
    # Вычисляем HMAC
    computed_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Сравниваем хэши с защитой от атак по времени
    result = hmac.compare_digest(computed_hash, received_hash)
    if result:
        return dict(data_pairs)