# 상품 가격 비교 크롤러

여러 쇼핑몰에서 키워드를 기반으로 상품 정보를 크롤링하고 MySQL에 저장하는 Python 크롤러입니다.  
Spring Boot 기반 상품 가격 비교 프로젝트에서 실시간 가격 정보를 수집하는 백엔드 크롤링 파이프라인 역할을 합니다.

---

## 기능 요약

- `keywords.txt`에 입력된 키워드로 크롤링 하고자 하는 쇼핑몰 검색
- Selenium을 활용한 JavaScript 렌더링 기반 크롤링
- 상품명, 가격, 이미지, 구매링크 등 추출
- 키워드 기반 자동 카테고리 분류
- MySQL 연동 및 DB 저장 (`products`, `product_images`, `product_prices` 테이블 등)

---

## 사용 기술

- Python 3.9
- Selenium
- webdriver-manager
- PyMySQL
- MySQL 8.0

---

## 프로젝트 구조

```text
project-root/
├── 11st/
│   ├── 11st_crawling.py
│   ├── keywords.txt
│   └── selectors.json
├── coupang/
│   └── coupang_crawling.py
├── auction/
│   └── auction_crawling.py
├── interpark/
│   └── interpark_crawling.py
└── README.md
```


## 의존성 설치

```bash
pip install -r requirements.txt
```

## .env

```.env
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "비밀번호",
    "database": "your_database",
    "charset": "utf8mb4",
    "autocommit": True
}
```

