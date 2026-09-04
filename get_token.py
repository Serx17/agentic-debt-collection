import json
import time
import jwt
import requests

def get_iam_token():
    # 1. Читаем секретный JSON-ключ
    with open('sa-key.json', 'r') as f:
        key_data = json.load(f)

    # 2. Формируем payload для JWT
    now = int(time.time())
    payload = {
        'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        'iss': key_data['service_account_id'],
        'iat': now,
        'exp': now + 3600
    }

    # 3. Подписываем JWT приватным ключом
    encoded_token = jwt.encode(
        payload,
        key_data['private_key'],
        algorithm='PS256',
        headers={'kid': key_data['id']}
    )

    # 4. Обмениваем JWT на IAM-токен
    response = requests.post(
        'https://iam.api.cloud.yandex.net/iam/v1/tokens',
        json={'jwt': encoded_token}
    )
    
    if response.status_code != 200:
        print(f"❌ Ошибка получения токена: {response.text}")
        return

    iam_token = response.json()['iamToken']
    
    print("="*70)
    print("✅ Твой свежий IAM_TOKEN (действует 12 часов):")
    print("="*70)
    print(iam_token)
    print("="*70)
    print("\n📋 Скопируй его и вставь в файл .env в переменную YANDEX_IAM_TOKEN")

if __name__ == "__main__":
    get_iam_token()