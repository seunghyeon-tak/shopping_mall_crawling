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


def load_selectors():
    with open("selectors.json", "r", encoding="utf-8") as f:
        return json.load(f)


def classify_category(keyword, category_map):
    for word, category in category_map.items():
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


def save_product(cursor, name, store_id, category_id, url, description):
    cursor.execute("SELECT id FROM products WHERE name = %s AND purchase_url = %s", (name, url))
    result = cursor.fetchone()
    if result:
        return result[0]
    cursor.execute("""
        INSERT INTO products (name, store_id, category_id, purchase_url, description)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, store_id, category_id, url, description))
    return cursor.lastrowid


def save_image(cursor, product_id, image_url):
    cursor.execute("SELECT id FROM product_images WHERE product_id = %s AND url = %s", (product_id, image_url))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO product_images (product_id, url, is_main)
            VALUES (%s, %s, %s)
        """, (product_id, image_url, 1))


def save_price(cursor, product_id, price):
    cursor.execute("""
        INSERT INTO product_prices (product_id, price, crawled_at)
        VALUES (%s, %s, %s)
    """, (product_id, price, datetime.now()))
