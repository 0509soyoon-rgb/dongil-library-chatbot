# 동일여고 AI 도서관 - 원본 검증 기능 추가 버전

이 버전은 업로드된 동일여고 소장도서 엑셀 원본을 기준으로만 작동합니다.

## 유지 원칙

- 원본 엑셀에 있는 도서만 검색/추천합니다.
- 제목, 저자, 출판사, 청구기호는 원본 값을 임의 수정하지 않습니다.
- 없는 책 제목을 만들어 추천하지 않습니다.
- 장르, 태그, 난이도, 추천 이유, 탐구주제, 간략 소개는 자동 보조 정보로 분리 표시합니다.

## 추가된 기능

- 난이도 재분류
  - 쉬움/보통이 과도하게 나오지 않도록 철학, 과학, 경제, 법, 고전, 원전, 전공 입문 도서는 상향 분류합니다.
- 책 간략 소개
  - 상세 페이지와 검색 카드에 1~2줄 자동 소개를 표시합니다.
  - 출판사 전문 줄거리가 아닌 자동 보조 소개임을 명시합니다.

## 실행

```bash
python -m pip install -r requirements.txt -i https://pypi.org/simple
python prepare_data.py
python -m uvicorn app.main:app --reload
```

브라우저에서 접속:

```text
http://127.0.0.1:8000
```

## Render 배포 명령

Build Command:

```bash
pip install -r requirements.txt && python prepare_data.py
```

Start Command:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
