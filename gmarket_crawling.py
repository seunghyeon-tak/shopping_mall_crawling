import time
import urllib.parse

import pymysql
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common import *


def search_gmarket_with_selenium(keyword, max_results=5):
    sel = load_selectors()["gmarket"]
    results = []

    try:
        driver = get_driver()
        url = f"https://browse.gmarket.co.kr/search?keyword={urllib.parse.quote(keyword)}"

        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel["item"])))

        items = driver.find_elements(By.CSS_SELECTOR, sel["item"])


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
    except Exception as e:
        print(f"[🚨] 전체 페이지 파싱 실패: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

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

        if not results:
            print("[⚠️] 크롤링 결과 없음, 건너뜀")
            continue

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
            save_price(cursor, product_id, store_id, r["price"])
            print(f"  ⤷ 저장 완료: {r['title']}")

        time.sleep(1)
    cursor.close()
    conn.close()
    print("\n[✅] G마켓 크롤링 완료!")


if __name__ == "__main__":
    main()
