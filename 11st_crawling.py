import time
import urllib.parse

import pymysql
import requests
from selenium.webdriver.common.by import By

from common import *


def search_11st_with_selenium(keyword, max_results=20):
    sel = load_selectors()["11st"]
    results = []

    try:
        driver = get_driver()
        encoded_keyword = urllib.parse.quote(keyword)
        url = f"https://search.11st.co.kr/Search.tmall?kwd={encoded_keyword}"

        driver.get(url)
        time.sleep(3)  # JS 렌더링 기다림

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
                    "price": float(price),
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


def extract_product_id_from_link(link):
    try:
        # 광고 리디렉션 링크인지 확인
        if "adoffice.11st.co.kr" in link:
            parsed = urllib.parse.urlparse(link)
            params = urllib.parse.parse_qs(parsed.query)
            redirect_url = params.get("redirect", [None])[0]
            if redirect_url:
                link = urllib.parse.unquote(redirect_url)  # URL 디코딩

        # 이제 정상적인 11번가 상품 URL이 됐으니 productId 추출
        match = re.search(r'/products/(?:pa/)?(\d+)', link)
        if match:
            return match.group(1)
        else:
            print(f"[⚠️] productId 추출 실패: {link}")
            return None

    except Exception as e:
        print(f"[🚨] productId 추출 중 에러: {e}")
        return None


def get_11st_key_features(product_id):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    url = f"https://apis.11st.co.kr/product/pd/v1/products/{product_id}/product-information"

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            print(f"[⚠️] 스펙 API 요청 실패: {response.status_code}")
            return json.dumps({})

        data = response.json()
        key_features = {}

        groups = data.get("data", {}).get("productInformationGroups", [])
        for group in groups:
            for item in group.get("productInformationItems", []):
                key = item["title"].strip().lower().replace(' ', '_')
                value = item["content"].strip()
                if key and value:
                    key_features[key] = value

        return json.dumps(key_features, ensure_ascii=False)

    except Exception as e:
        print(f"[🚨] 스펙 API 호출 실패: {e}")
        return json.dumps({})


def main():
    with open("keywords.txt", "r", encoding="utf-8") as f:
        keywords = [line.strip() for line in f if line.strip()]

    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    store_id = get_or_create_id(cursor, "stores", "11번가")

    for keyword in keywords:
        print(f"\n[🔍] 크롤링 중: {keyword}")
        category_name = classify_category(keyword)
        category_id = get_or_create_id(cursor, "categories", category_name)

        results = search_11st_with_selenium(keyword)

        if not results:
            print("[⚠️] 크롤링 결과 없음, 건너뜀")
            continue

        for r in results:
            product_id = extract_product_id_from_link(r["link"])
            if not product_id:
                continue

            key_features_json = get_11st_key_features(product_id)

            product_id = save_product(
                cursor,
                name=r["title"],
                store_id=store_id,
                category_id=category_id,
                url=r["link"],
                description="",
                key_features=key_features_json
            )
            save_image(cursor, product_id, r["image"])
            save_price(cursor, product_id, store_id, r["price"])
            print(f"  ⤷ 저장 완료: {r['title']}")

        time.sleep(1)

    cursor.close()
    conn.close()
    print("\n[✅] 11번가 크롤링 완료!")


if __name__ == "__main__":
    main()
