import json
import os
import re
import time
import urllib.parse
from datetime import datetime

import pymysql
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
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

category_map = {
    "디지털 도어락": "스마트홈",
    "게이밍 마우스": "입력기기",
    "노트북 받침대": "노트북 액세서리",
    "차량용 무선 충전기": "차량용 디지털",
    "PC 스피커": "오디오",
    "HDMI 분배기": "영상장비",
    "기계식 키보드": "입력기기",
    "디지털 타이머": "소형가전",
    "전자노트": "전자문구",
    "USB C to HDMI 케이블": "영상장비"
}

with open("../selectors.json", "r", encoding="utf-8") as f:
    SELECTORS = json.load(f)


def classify_category(keyword):
    for word, category in category_map.items():
        if word in keyword:
            return category
    return "기타"


def parse_price(price_str):
    match = re.search(r"\d[\d,]*", price_str)
    if match:
        return float(match.group().replace(",", ""))
    return None


def get_driver():
    options = Options()
    options.add_argument("--headless=new")  # 최신 방식 headless
    options.add_argument("--disable-blink-features=AutomationControlled")  # 자동화 감지 우회
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")  # 진짜 브라우저처럼 위장
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
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


def search_gmarket_with_selenium(keyword, max_results=5):
    sel = SELECTORS["gmarket"]

    driver = get_driver()
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://browse.gmarket.co.kr/search?keyword={encoded_keyword}"

    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel["item"])))

    items = driver.find_elements(By.CSS_SELECTOR, sel["item"])
    results = []

    for item in items[:max_results]:
        try:
            title = item.find_element(By.CSS_SELECTOR, sel["title"]).text
            price = parse_price(item.find_element(By.CSS_SELECTOR, sel["price"]).text)
            if price is None:
                print(f"[❗] 가격 파싱 실패 → '{price}'")
                continue

            link = item.find_element(By.CSS_SELECTOR, sel["link"]).get_attribute("href")
            image = item.find_element(By.CSS_SELECTOR, sel["image"]).get_attribute("src")

            results.append({
                "title": title,
                "price": price,
                "link": link,
                "image": image
            })

        except Exception as e:
            print(f"[⚠️] 상품 파싱 실패: {e}")
            continue

    driver.quit()
    return results


def main():
    with open("keywords.txt", "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    store_id = get_or_create_id(cursor, "stores", "G마켓")

    for keyword in keywords:
        print(f"\n[🔍] 크롤링 중: {keyword}")
        category_name = classify_category(keyword)
        category_id = get_or_create_id(cursor, "categories", category_name)

        results = search_gmarket_with_selenium(keyword)

        for r in results:
            product_id = save_product(
                cursor,
                name=r["title"],
                store_id=store_id,
                category_id=category_id,
                url=r["link"],
                description=""
            )
            save_image(cursor, product_id, r["image"])
            save_price(cursor, product_id, r["price"])
            print(f"  ⤷ 저장 완료: {r['title']}")

        time.sleep(1)
    cursor.close()
    conn.close()
    print("\n[✅] G마켓 크롤링 완료!")


if __name__ == "__main__":
    main()
