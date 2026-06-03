from __future__ import annotations
import os, sqlite3, random, hashlib, re
from datetime import date
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
DB_FILE = BASE / "library.db"
app = FastAPI(title="동일여고 진로독서 챗봇")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

CAREER_ALIASES = {
    "의사":"의학/보건", "의대":"의학/보건", "간호":"의학/보건", "약사":"의학/보건", "보건":"의학/보건", "생명":"의학/보건",
    "ai":"AI/컴퓨터", "인공지능":"AI/컴퓨터", "컴공":"AI/컴퓨터", "컴퓨터":"AI/컴퓨터", "개발자":"AI/컴퓨터", "데이터":"AI/컴퓨터", "코딩":"AI/컴퓨터",
    "교사":"교육/교사", "교육":"교육/교사", "선생님":"교육/교사", "수학교사":"교육/교사",
    "수학":"수학/공학", "공학":"수학/공학", "건축":"수학/공학", "물리":"수학/공학", "우주":"수학/공학",
    "법":"법/정치/사회", "변호사":"법/정치/사회", "정치":"법/정치/사회", "사회":"법/정치/사회", "경찰":"법/정치/사회", "기자":"법/정치/사회",
    "경제":"경영/경제", "경영":"경영/경제", "회계":"경영/경제", "마케팅":"경영/경제", "창업":"경영/경제",
    "심리":"심리/상담", "상담":"심리/상담", "마음":"심리/상담",
    "문학":"언론/문학/인문", "작가":"언론/문학/인문", "역사":"언론/문학/인문", "철학":"언론/문학/인문", "인문":"언론/문학/인문",
    "미술":"예술/디자인", "디자인":"예술/디자인", "음악":"예술/디자인", "영화":"예술/디자인", "예술":"예술/디자인",
    "환경":"환경/생태", "기후":"환경/생태", "생태":"환경/생태", "동물":"환경/생태", "지구":"환경/생태",
}
DIFFICULTY_WORDS = {"쉬운":(1,2), "가벼운":(1,2), "입문":(1,2), "고1":(1,2), "보통":(2,3), "도전":(3,4), "심화":(4,5), "어려운":(4,5), "전문":(5,5)}

TITLE_STOPWORDS = [
    "추천", "책", "도서", "관련", "해줘", "찾아줘", "알려줘", "검색", "있어", "있나요",
    "설명", "줄거리", "내용", "정보", "뭐야", "무엇", "읽고", "싶어", "대한", "에 대해", "은", "는", "이", "가"
]
RECOMMEND_INTENT_WORDS = ["추천", "진로", "학과", "생기부", "세특", "탐구", "오늘", "운명", "뽑기", "랜덤", "아무거나", "쉬운", "심화", "어려운"]

def normalize_title(text: str) -> str:
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", (text or "").lower())

def clean_title_query(text: str) -> str:
    q = (text or "").strip()
    q = re.sub(r"[?!.,~]+", " ", q)
    for w in TITLE_STOPWORDS:
        q = q.replace(w, " ")
    q = re.sub(r"\s+", " ", q).strip()
    return q

def find_title_match(text: str):
    """
    책 제목 검색용 함수.
    1) 제목이 정확히 같은 책
    2) 제목이 검색어로 시작하는 책
    3) 제목에 검색어가 포함된 책
    순서로 한 권을 고른다.
    """
    q = clean_title_query(text)
    nq = normalize_title(q)
    if len(nq) < 2:
        return None

    with conn() as con:
        rows = con.execute(
            """
            SELECT * FROM books
            WHERE title LIKE ?
            LIMIT 80
            """,
            (f"%{q}%",)
        ).fetchall()

    if not rows:
        return None

    def score(row):
        title = row["title"] or ""
        nt = normalize_title(title)
        if nt == nq:
            group = 0
        elif nt.startswith(nq):
            group = 1
        elif nq in nt:
            group = 2
        else:
            group = 9
        # 같은 조건이면 제목이 짧은 책을 우선한다.
        return (group, len(nt), row["id"])

    best = sorted(rows, key=score)[0]
    if score(best)[0] >= 9:
        return None
    return dict(best)

def looks_like_title_search(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    # 추천/진로 요청이면 제목 상세 검색보다 추천을 우선한다.
    if any(w in t for w in RECOMMEND_INTENT_WORDS):
        return False
    return find_title_match(t) is not None

class ChatIn(BaseModel):
    message: str


def conn():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con

def rows_to_books(rows):
    return [dict(r) for r in rows]

def book_query(where="1=1", params=(), limit=6, order="RANDOM()"):
    with conn() as con:
        return rows_to_books(con.execute(f"SELECT * FROM books WHERE {where} ORDER BY {order} LIMIT ?", (*params, limit)).fetchall())

def search_books(text: str, limit=6):
    words = [w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", text) if w not in ["추천", "책", "도서", "관련", "해줘", "찾아줘"]]
    career = detect_career(text)
    clauses, params = [], []
    if career:
        clauses.append("careers LIKE ?"); params.append(f"%{career}%")
    for w in words[:5]:
        clauses.append("(title LIKE ? OR author LIKE ? OR publisher LIKE ? OR genre LIKE ? OR tags LIKE ? OR careers LIKE ? OR subjects LIKE ?)")
        params.extend([f"%{w}%"]*7)
    where = " OR ".join(clauses) if clauses else "1=1"
    min_d, max_d = detect_difficulty(text)
    if min_d:
        where = f"({where}) AND difficulty BETWEEN ? AND ?"; params.extend([min_d, max_d])
    return book_query(where, tuple(params), limit=limit)

def detect_career(text: str):
    low = text.lower().replace(" ", "")
    # longer aliases first
    for k in sorted(CAREER_ALIASES, key=len, reverse=True):
        if k.lower().replace(" ", "") in low:
            return CAREER_ALIASES[k]
    return None

def detect_difficulty(text: str):
    for k, v in DIFFICULTY_WORDS.items():
        if k in text:
            return v
    m = re.search(r"난이도\s*([1-5])", text)
    if m:
        n=int(m.group(1)); return n,n
    return (None,None)

def daily_books(limit=3, career=None):
    seed = int(hashlib.sha256(str(date.today()).encode()).hexdigest()[:8], 16)
    where, params = "1=1", []
    if career:
        where="careers LIKE ?"; params=[f"%{career}%"]
    # deterministic random by id+seed
    with conn() as con:
        rows = con.execute(f"SELECT * FROM books WHERE {where}", params).fetchall()
    if not rows: return []
    rng = random.Random(seed + (hash(career) if career else 0))
    picked = rng.sample(rows, min(limit, len(rows)))
    return rows_to_books(picked)

def format_intro(kind, books, extra=""):
    if not books:
        return {"reply":"조건에 맞는 책을 찾지 못했어요. 진로명이나 관심 키워드를 조금 다르게 입력해 보세요.", "books":[]}
    return {"reply": kind + ("\n" + extra if extra else ""), "books": books}

def handle_chat(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"reply":"원하는 진로, 학과, 관심사, 난이도를 입력해 주세요. 예: '고1이 읽기 쉬운 의학 책 추천'", "books":[]}
    # 책 제목만 입력한 경우에는 추천 목록이 아니라 그 책의 상세 정보를 먼저 보여준다.
    # 예: "소나기", "데미안", "아몬드 줄거리"
    title_match = None
    if not any(w in text for w in RECOMMEND_INTENT_WORDS):
        title_match = find_title_match(text)
    if title_match:
        return {
            "reply": f"『{title_match.get('title', '')}』 도서 정보입니다.",
            "books": [title_match],
            "mode": "book_detail"
        }

    career = detect_career(text)
    if any(w in text for w in ["오늘", "오늘의", "데일리"]):
        books = daily_books(3, career)
        label = f"오늘의 {career} 독서 추천입니다." if career else "오늘의 독서 추천입니다."
        return format_intro(label, books, "매일 날짜가 바뀌면 추천도 달라져요.")
    if any(w in text for w in ["운명", "뽑기", "랜덤", "아무거나"]):
        books = book_query("careers LIKE ?" if career else "1=1", (f"%{career}%",) if career else (), limit=1)
        return format_intro("운명의 책을 한 권 뽑았습니다.", books)
    books = search_books(text, limit=6)
    if any(w in text for w in ["생기부", "세특", "탐구", "주제"]):
        return format_intro("생기부·탐구활동에 연결하기 좋은 책입니다.", books, "각 카드의 '탐구주제'를 참고하세요.")
    if any(w in text for w in ["학과", "진학", "되고 싶", "진로", "관련"]):
        label = f"{career} 진로와 연결되는 책을 골랐습니다." if career else "입력한 관심사와 연결되는 진로독서 책을 골랐습니다."
        return format_intro(label, books)
    return format_intro("입력한 내용과 관련 있는 책을 찾았습니다.", books)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/today")
def api_today(career: str | None = None):
    return {"books": daily_books(3, career)}

@app.post("/api/chat")
def api_chat(data: ChatIn):
    return JSONResponse(handle_chat(data.message))

@app.get("/api/health")
def health():
    exists = DB_FILE.exists()
    count = 0
    if exists:
        with conn() as con:
            count = con.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    return {"ok": exists and count > 0, "books": count}
