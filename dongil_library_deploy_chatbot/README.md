# 동일여고 진로독서 챗봇

학생들이 URL만 눌러 접속할 수 있도록 만든 배포형 FastAPI 웹앱입니다.

## 포함 기능

- 오늘의 독서 추천
- 운명의 책 뽑기
- 진로/학과/관심사 기반 도서 추천
- 생기부·세특 탐구주제 추천
- 도서별 난이도 표시: 입문~전문, 별점 1~5
- 관련 교과, 관련 진로, 태그, 추천 이유 자동 생성
- Render 배포 설정 포함

## VS Code에서 실행

```bash
python -m pip install -r requirements.txt -i https://pypi.org/simple
python prepare_data.py
python -m uvicorn app.main:app --reload
```

브라우저에서 접속:

```text
http://127.0.0.1:8000
```

## 학생들이 바로 접속하는 사이트로 배포하기: Render

1. GitHub 계정을 만듭니다.
2. 이 폴더를 GitHub 저장소에 올립니다.
3. Render에 로그인합니다.
4. New + → Web Service 선택
5. GitHub 저장소 연결
6. 설정값:

```text
Build Command: pip install -r requirements.txt
Start Command: python prepare_data.py && python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

7. 배포가 끝나면 Render가 접속 주소를 줍니다.
8. 그 주소를 QR코드로 만들어 학생들에게 공유하면 됩니다.

## 파일 구조

```text
app/main.py              서버와 추천 API
app/templates/index.html 화면
app/static/app.js        챗봇 동작
app/static/style.css     디자인
prepare_data.py          엑셀 → SQLite 변환 및 자동 태그/난이도 생성
data/books.xlsx          동일여고 소장도서 목록
render.yaml              Render 배포 설정
Procfile                 배포 실행 설정
requirements.txt         필요한 파이썬 패키지
```

## 데이터 다시 넣기

새 도서 목록 엑셀을 `data/books.xlsx` 이름으로 바꿔 넣고 아래 명령어를 다시 실행하세요.

```bash
python prepare_data.py
```
