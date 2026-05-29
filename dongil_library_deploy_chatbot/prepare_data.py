from __future__ import annotations
import os, re, sqlite3, json, hashlib
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "data" / "books.xlsx"
DB_FILE = BASE / "app" / "library.db"

CAREERS = {
    "의학/보건": {"keywords": ["의학","의사","간호","보건","질병","병원","생명","인체","바이러스","감염","약","면역","유전자","뇌","건강"], "subjects":["생명과학","화학","윤리"], "jobs":["의사","간호사","약사","보건교사","의생명 연구원"]},
    "AI/컴퓨터": {"keywords": ["인공지능","AI","알고리즘","코딩","컴퓨터","프로그래밍","데이터","로봇","소프트웨어","디지털","챗GPT","빅데이터"], "subjects":["정보","수학","기술"], "jobs":["AI 개발자","데이터사이언티스트","소프트웨어 개발자","로봇공학자"]},
    "교육/교사": {"keywords": ["교육","교사","학교","수업","청소년","학습","아이들","교실","공부","선생님"], "subjects":["교육학","국어","사회"], "jobs":["교사","교육연구원","상담교사","교육기획자"]},
    "수학/공학": {"keywords": ["수학","공학","물리","우주","기계","건축","과학","통계","미적분","기하","확률","수"], "subjects":["수학","물리학","기술"], "jobs":["공학자","수학교사","통계학자","건축가","물리학자"]},
    "법/정치/사회": {"keywords": ["법","정의","정치","사회","인권","민주","국가","경제","헌법","범죄","재판","평등","노동"], "subjects":["사회","정치와 법","윤리"], "jobs":["변호사","검사","공무원","사회학자","기자"]},
    "경영/경제": {"keywords": ["경제","경영","돈","투자","마케팅","기업","회계","금융","브랜드","창업","시장"], "subjects":["경제","사회","수학"], "jobs":["경영인","회계사","마케터","금융전문가","창업가"]},
    "심리/상담": {"keywords": ["심리","마음","감정","상담","관계","우울","자존감","행복","불안","성격"], "subjects":["심리학","윤리","사회"], "jobs":["상담사","임상심리사","교사","사회복지사"]},
    "언론/문학/인문": {"keywords": ["문학","소설","시","작가","글쓰기","철학","역사","인문","고전","문명","언어","독서"], "subjects":["국어","문학","역사","철학"], "jobs":["작가","기자","출판기획자","인문학 연구자"]},
    "예술/디자인": {"keywords": ["미술","디자인","음악","영화","사진","예술","건축","패션","그림","창작"], "subjects":["미술","음악","기술","문학"], "jobs":["디자이너","예술가","건축가","영상기획자"]},
    "환경/생태": {"keywords": ["환경","기후","생태","지구","동물","식물","바다","숲","탄소","멸종","에너지"], "subjects":["생명과학","지구과학","사회"], "jobs":["환경공학자","생태학자","환경정책가","과학자"]},
}

KDC_GENRES = [
    ("000", "총류/정보"), ("100", "철학/심리"), ("200", "종교"), ("300", "사회과학"),
    ("400", "자연과학"), ("500", "기술과학"), ("600", "예술"), ("700", "언어"),
    ("800", "문학"), ("900", "역사/지리"),
]

def clean(x: object) -> str:
    if pd.isna(x): return ""
    return re.sub(r"\s+", " ", str(x)).strip()

def kdc_from_call(call: str) -> str:
    m = re.search(r"(\d{3})", call or "")
    return m.group(1) if m else ""

def genre_from_call(call: str, title: str) -> str:
    code = kdc_from_call(call)
    if code:
        n = int(code[:1]) * 100
        for prefix, genre in KDC_GENRES:
            if int(prefix) == n:
                return genre
    t = title
    for g, meta in CAREERS.items():
        if any(k.lower() in t.lower() for k in meta["keywords"]):
            return g
    return "일반/교양"

def match_careers(text: str, genre: str) -> list[str]:
    scores = []
    low = text.lower()
    for career, meta in CAREERS.items():
        score = 0
        if career in genre: score += 3
        for kw in meta["keywords"]:
            if kw.lower() in low: score += 2
        if score: scores.append((score, career))
    if not scores:
        if "문학" in genre: return ["언론/문학/인문"]
        if "사회" in genre: return ["법/정치/사회"]
        if "자연" in genre: return ["수학/공학", "환경/생태"]
        return ["언론/문학/인문"]
    return [c for _, c in sorted(scores, reverse=True)[:3]]

def difficulty(title: str, call: str, pub_year: str, genre: str) -> tuple[int, str]:
    text = f"{title} {call} {genre}"
    score = 2
    hard = ["원론", "철학", "고전", "비판", "경제학", "수학", "물리", "법학", "정치", "심화", "전문", "학술", "논문", "이론", "역사"]
    easy = ["만화", "그림", "청소년", "쉽게", "처음", "입문", "하루", "이야기", "소설", "에세이", "동화"]
    if any(w in text for w in easy): score -= 1
    if any(w in text for w in hard): score += 1
    code = kdc_from_call(call)
    if code:
        try:
            num = int(code[:3])
            if 100 <= num < 200 or 300 <= num < 600: score += 1
            if 800 <= num < 900: score -= 1
        except Exception: pass
    score = max(1, min(5, score))
    labels = {1:"입문",2:"보통",3:"도전",4:"심화",5:"전문"}
    return score, labels[score]

def tags_for(title: str, author: str, genre: str, careers: list[str], diff_label: str) -> list[str]:
    tags = [genre, diff_label]
    for c in careers: tags.append(c)
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", title)
    for w in words[:4]:
        if w not in tags: tags.append(w)
    return tags[:8]

def summary_reason(title: str, author: str, genre: str, careers: list[str], subjects: list[str], diff_label: str):
    c = ", ".join(careers[:2])
    s = ", ".join(subjects[:3])
    summary = f"『{title}』은 {genre} 분야의 도서로, {c} 진로와 연결해 읽기 좋습니다. {s} 교과와 연계해 개념, 사례, 관점을 정리하는 데 도움이 됩니다."
    reason = f"{diff_label} 수준으로 접근할 수 있으며, 진로 독서나 탐구 활동에서 자신의 관심 분야를 설명할 근거를 만들기 좋습니다."
    topic = f"'{title}'을 바탕으로 {s}와 관련된 사회적 의미, 기술 변화, 윤리적 쟁점을 탐구해 보기"
    return summary, reason, topic

def build():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"{DATA_FILE} 파일이 없습니다.")
    df = pd.read_excel(DATA_FILE, sheet_name=0)
    rows = []
    seen = set()
    for _, r in df.iterrows():
        title = clean(r.get("자료명"))
        if not title: continue
        author = clean(r.get("저자"))
        publisher = clean(r.get("출판사"))
        year = clean(r.get("출판년도"))
        call = clean(r.get("청구기호"))
        regno = clean(r.get("등록번호"))
        loc = clean(r.get("소장처"))
        key = (title, author, publisher, year)
        if key in seen: continue
        seen.add(key)
        genre = genre_from_call(call, title)
        text = f"{title} {author} {publisher} {genre} {call}"
        careers = match_careers(text, genre)
        subjects = []
        for c in careers:
            subjects += CAREERS.get(c, {}).get("subjects", [])
        subjects = list(dict.fromkeys(subjects))[:5] or ["국어", "사회"]
        d, dl = difficulty(title, call, year, genre)
        tags = tags_for(title, author, genre, careers, dl)
        summary, reason, topic = summary_reason(title, author, genre, careers, subjects, dl)
        rows.append({
            "title": title, "author": author, "publisher": publisher, "year": year, "call_number": call,
            "reg_no": regno, "location": loc, "genre": genre, "tags": ", ".join(tags),
            "careers": ", ".join(careers), "subjects": ", ".join(subjects),
            "difficulty": d, "difficulty_label": dl, "summary": summary,
            "recommendation_reason": reason, "exploration_topic": topic,
        })
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS books")
    cur.execute("""
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, author TEXT, publisher TEXT, year TEXT, call_number TEXT,
            reg_no TEXT, location TEXT, genre TEXT, tags TEXT, careers TEXT, subjects TEXT,
            difficulty INTEGER, difficulty_label TEXT, summary TEXT, recommendation_reason TEXT,
            exploration_topic TEXT
        )
    """)
    cur.executemany("""
        INSERT INTO books (title, author, publisher, year, call_number, reg_no, location, genre, tags, careers, subjects, difficulty, difficulty_label, summary, recommendation_reason, exploration_topic)
        VALUES (:title, :author, :publisher, :year, :call_number, :reg_no, :location, :genre, :tags, :careers, :subjects, :difficulty, :difficulty_label, :summary, :recommendation_reason, :exploration_topic)
    """, rows)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_books_text ON books(title, author, publisher, genre, tags, careers)")
    con.commit(); con.close()
    print(f"완료: {len(rows)}권을 {DB_FILE}에 저장했습니다.")

if __name__ == "__main__":
    build()
