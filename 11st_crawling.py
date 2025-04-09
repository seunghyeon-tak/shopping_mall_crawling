import time
import urllib.parse

import pymysql
from selenium.webdriver.common.by import By

from common import *

# 카테고리 매핑
category_map = {
    "에어팟": "이어폰",
    "버즈": "이어폰",
    "충전기": "충전기",
    "케이블": "충전기",
    "키보드": "입력기기",
    "마우스": "입력기기",
    "보조배터리": "충전기",
    "모니터": "디스플레이",
    "헤드폰": "이어폰",
    "스마트워치": "웨어러블",
    "케이스": "스마트폰 액세서리"
}


def search_11st_with_selenium(keyword, max_results=5):
    sel = load_selectors()["11st"]

    driver = get_driver()
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://search.11st.co.kr/Search.tmall?kwd={encoded_keyword}"

    driver.get(url)
    time.sleep(3)  # JS 렌더링 기다림

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
                "price": float(price),
                "link": link,
                "image": image
            })
        except Exception as e:
            print(f"[⚠️] 상품 파싱 실패: {e}")
            continue

    driver.quit()
    return results


def main():
    with open("11st/keywords.txt", "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    store_id = get_or_create_id(cursor, "stores", "11번가")

    for keyword in keywords:
        print(f"\n[🔍] 크롤링 중: {keyword}")
        category_name = classify_category(keyword)
        category_id = get_or_create_id(cursor, "categories", category_name)

        results = search_11st_with_selenium(keyword)
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
    print("\n[✅] 크롤링 + DB 저장 완료!")


if __name__ == "__main__":
    main()
