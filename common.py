import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "autocommit": True
}

UNIFIED_CATEGORY_MAP = {
    "에어팟": "이어폰",
    "버즈": "이어폰",
    "헤드폰": "이어폰",
    "충전기": "충전기",
    "케이스": "스마트폰 액세서리",
    "마우스": "입력기기",
    "키보드": "입력기기",
    "보조배터리": "충전기",
    "모니터": "모니터",
    "스마트워치": "웨어러블",
    "스트랩": "웨어러블",
    "도어락": "스마트홈",
    "노트북 받침대": "노트북 액세서리",
    "차량용 무선 충전기": "차량용 디지털",
    "스피커": "오디오",
    "HDMI 분배기": "영상장비",
    "USB C to HDMI": "영상장비",
    "타이머": "소형가전",
    "전자노트": "전자문구"
}


def load_selectors():
    with open("selectors.json", "r", encoding="utf-8") as f:
        return json.load(f)


def classify_category(keyword):
    # 카테고리 매핑
    for word, category in UNIFIED_CATEGORY_MAP.items():
        if word in keyword:
            return category
    return "기타"


def parse_price(price_str):
    # 가격에서 가장 앞에 나오는 숫자 하나 추출
    match = re.search(r"\d[\d,]*", price_str)
    if match:
        return float(match.group().replace(",", ""))
    return None


def get_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    )
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_or_create_id(cursor, table, name):
    cursor.execute(f"SELECT id FROM {table} WHERE name = %s", (name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    cursor.execute(f"INSERT INTO {table} (name) VALUES (%s)", (name,))
    return cursor.lastrowid


def save_product(cursor, name, store_id, category_id, url, description, key_features="{}"):
    cursor.execute("SELECT id FROM products WHERE name = %s AND purchase_url = %s", (name, url))
    result = cursor.fetchone()
    if result:
        return result[0]
    cursor.execute("""
        INSERT INTO products (name, store_id, category_id, purchase_url, description, key_features, is_active, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (name, store_id, category_id, url, description, key_features, True, datetime.now()))
    return cursor.lastrowid


def save_image(cursor, product_id, image_url):
    cursor.execute("SELECT id FROM product_images WHERE product_id = %s AND url = %s", (product_id, image_url))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO product_images (product_id, url, is_main)
            VALUES (%s, %s, %s)
        """, (product_id, image_url, 1))


def save_price(cursor, product_id, store_id, price):
    cursor.execute("""
        INSERT INTO product_prices (product_id, store_id, price, crawled_at)
        VALUES (%s, %s, %s, %s)
    """, (product_id, store_id, price, datetime.now()))
