import time
import urllib.parse

import pymysql
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common import *

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


def search_gmarket_with_selenium(keyword, max_results=5):
    sel = load_selectors()["gmarket"]

    driver = get_driver()
    url = f"https://browse.gmarket.co.kr/search?keyword={urllib.parse.quote(keyword)}"

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
    with open("gmarket/keywords.txt", "r", encoding="utf-8") as f:
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
