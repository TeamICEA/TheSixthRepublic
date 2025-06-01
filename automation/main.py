import pymysql
import psycopg2
import requests
import json
import re
from openai import OpenAI
from bs4 import BeautifulSoup

keys = {}
with open("keys.json") as f:
    keys = json.load(f)
# con = pymysql.connect(host=keys["SQL_HOST"], user=keys["SQL_USERNAME"], password=keys["SQL_PASSWORD"], database=keys["SQL_DATABASE"], port=3306, use_unicode=True, charset='utf8')
con = psycopg2.connect(host=keys["SQL_HOST"], dbname=keys["SQL_DATABASE"],user=keys["SQL_USERNAME"],password=keys["SQL_PASSWORD"],port=5432)
cur = con.cursor()
client = OpenAI(api_key=keys["OPENAI_KEY"])

def execute():
    global cur

    filename = input("파일 이름을 입력하세요: ")
    f = open(filename, "r")
    lines = f.read()
    cur.execute(lines)

def view():
    global cur
    
    cur.execute("select * from categories;")
    rows = cur.fetchall()

    for row in rows:
        print(row)

def crawl_minjoo():
    for i in range(1201498, 1211003):
        response = requests.get(f"https://theminjoo.kr/main/sub/news/view.php?sno=0&brd=230&post={i}")

        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            texts = soup.select_one("#container > div.article-body > div > div.board-view__wrap > div.board-view > div.board-view__body")
            
            print(texts.text)

def crawl_all_articles():
    # YH STYLE
    global con

    for i in range(1, 21):
        url = f"https://www.yna.co.kr/politics/all/{i}"

        response = requests.get(url)

        if response.status_code != 200:
            break
        
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("#container > div.container521 > div.content03 > div.section01 > section > div > ul > li")

        print(f"The number of article: {len(articles)}")
        for article in articles:
            url_a = article.select_one("div > div > strong > a")

            if url_a is not None:
                url = url_a["href"]
                crawl_one_article(url)
        print(f"DONE!")
        con.commit()

def get_article_raw(url: str, title_selector: str, contents_selector: str) -> tuple[str, str]:
    response_text = ""

    try:
        response = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
                "Referer": "https://www.google.com/",
                "Connection": "keep-alive"
            })

        if response.status_code != 200:
            return "", ""
        
        response_text = response_text
    except:
        pass
    
    if response_text == "":
        return "", ""

    html = response_text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one(title_selector)
    title_text = ""
    contents = soup.select_one(contents_selector)
    contents_text = ""

    if title is not None:
        title_text = title.text
    if contents is not None:
        contents_text = contents.text

    return title_text, contents_text

def get_article_naver(url: str) -> tuple[str, str]:
    return get_article_raw(url, "#title_area > span", "#dic_area")

def get_article_yh(url: str) -> tuple[str, str]:
    return get_article_raw(url, "#container > div.container591 > div.content90 > header > h1", "#articleWrap > div.story-news.article")

def gpt(content: str) -> str:
    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    store=False,
    messages=[
        {"role": "user", "content": content}
    ]
    )

    return completion.choices[0].message.content

def find_id(sql: str) -> str:
    sql2 = sql.replace("INSERT INTO stances (id, category_id, position_summary, position_score, source_url) VALUES (", "")
    sql3 = ""

    for i in range(0, len(sql2)):
        if sql2[i] == ',':
            break
        sql3 += sql2[i]

    sql3 = sql3.replace("'", "")
    sql3 = sql3.replace('"', '')
    return sql3

def crawl_one_article(url: str):
    global client, cur

    title, contents = get_article_yh(url)
    question = f"""# {title}
{contents}

ㅡㅡㅡㅡㅡㅡㅡㅡㅡ
이 문장들이 핵심 데이터고, 이 문장들을 기반으로 너는 INSERT 명령어를 채워야 해.

각각 category 테이블의 데이터로, 필드는 id, name, description, parent_id야
'1', '경제 정책', '시장 자유도, 복지, 조세 정책\n자유시장 vs 복지국가', NULL
'2', '사회 이슈', '여성, 성소수자, 다문화 수용\n보수적 vs 진보적', NULL
'3', '국가 안보', '대북정책, 국방 강화\n강경 대응 vs 평화 협력', NULL
'4', '법과 질서', '범죄 처벌, 사형제도\n강력 처벌 vs 인권 중심', NULL
'5', '교육 정책', '교육 자율성, 입시 제도\n경쟁 중심 vs 공정·형평', NULL
'6', '환경 정책', '기후변화 대응, 탄소세\n산업 우선 vs 환경 보호', NULL
'7', '노동·고용', '비정규직, 최저임금, 주 4일제\n노동자 권리 vs 기업 자율', NULL
'8', '종교와 정치', '종교적 영향력\n세속주의 vs 전통가치 중시', NULL
'9', '언론/표현의 자유', '허위 정보, 검열, 표현 규제\n자유 보장 vs 질서 유지', NULL
'10', '정치 제도 개혁', '선거제도, 국회의원 수\n현행 유지 vs 제도 개편', NULL
'11', '부동산·주거 정책', '공급 확대, 공공주택, 세금 정책 등', NULL
'12', '보건의료 정책', '공공의료 확대, 건강보험, 의료 인프라', NULL
'13', '청년/고령층 정책', '청년 지원, 고령화 대책, 세대 간 형평성', NULL
'14', '중소기업·자영업', '지원 정책, 세제 혜택, 규제 완화 등', NULL
'15', '디지털/과학기술', '디지털 전환, AI/로봇, R&D 투자', NULL
'16', '행정·지방자치', '지방분권, 행정 효율화, 공무원 제도', NULL

이게 category야

각각 stances 테이블의 필드명, 타입, 설명
id, TEXT, 정치인 이름
category_id, INT, 정책 분야 ID
position_summary, TEXT, 요약된 입장
position_score, FLOAT, 성향 점수 (-1 ~ 1 사이 예: -1 보수 0 중립 1 진보 등)
source_url, TEXT, 뉴스/공약 링크 등 출처

source_url은 {url}로 고정시켜주고
너가 id, category_id, position_summary, position_score을 채워주면 돼.
position_summary는 몇문장으로 압축해야돼
position_score는 float로 -1과 1사이를 조정할 수 있어. 소수값도 허용이고
-1이 보수, 0이 중립, 1이 진보야.

INSERT INTO stances (id, category_id, position_summary, position_score, source_url) VALUES (...);

이 명령어의 VALUES 안에 있는 걸 너가 채워주고 답변을 INSERT 명령어로만 해줘 
INSERT 명령어 하나로만 답변해. 마지막엔 세미콜론 (;) 붙여주고. **마크다운 문법없이, 특수문자 '나 "가 들어가는 일 없이, raw text로 출력해.**"""

    sql = gpt(question)
    name = find_id(sql)

    cur.execute(f"select str_id from politicians where name='{name}';")
    rows = cur.fetchall()

    if len(rows) == 0:
        return

    sql = sql.replace(f"'{name}'", f"'{str(rows[0][0])}'")
    sql = sql.replace(f'"{name}"', f'"{str(rows[0][0])}"')
    print(sql)
    cur.execute(sql)

CLEANR = re.compile('<.*?>')

def cleanhtml(raw_html):
  cleantext = re.sub(CLEANR, '', raw_html)
  return cleantext

def crawl_all_v2(reverse=False, start_from=""):
    politicians = []
    politicians2 = []
    keywords = []
    start = True

    cur.execute("select id, name, description from categories;")
    rows = cur.fetchall()

    for row in rows:
        keywords.append(row)
    
    cur.execute("select str_id, name from politicians;")
    rows = cur.fetchall()

    for row in rows:
        politicians.append(row)

    if reverse:
        keywords.reverse()

    if start_from != "":
        start = False
    
    for politician in politicians:
        if start_from != "" and politician[1] == start_from:
            start = True
        if not start:
            continue

        politicians2.append(politician)

    gongyak = False

    for keyword in keywords:
        keywords2 = str(keyword[2]).split(",")

        for keyword2 in keywords2:
            keyword2 = keyword2.strip(" ")

            for politician in politicians2:
                category = f"{politician[1]} {keyword2}"

                if keyword2 == "공약":
                    if gongyak:
                        continue
                    gongyak = True

                articles = crawl_v2(category, 1, 10)

                for article in articles:
                    query = f"""# {article[0]}
    {article[3]}

    ㅡㅡㅡㅡㅡㅡㅡㅡㅡ
    이 문장들이 핵심 데이터고, 이 문장들을 기반으로 너는 답변해야 해.

    너가 서술해야 할 구조 형식을 이제 알려줄게.
    
    ㅡㅡㅡㅡㅡ
    [카테고리] [정치인 이름]은(는) [공약/발언/행적]을 통해 [정책 방향성]을 강조하였다. 예를 들어, "[대표 발언 또는 주요 표현]" 등이 있다.
    ㅡㅡㅡㅡ
    이 문장이 너가 맞춰야 할 구조 형식이야.
    또한, 문장을 생성하면서 "이나 '같은 특수문자를 넣으면 절대 안돼.

    문장 구조를 잘 갖춘 예: [환경·에너지관] 이재명은 재생에너지 중심의 에너지 전환 정책을 추진하며, 탈원전을 선언하였다. 예를 들어, "2050년까지 원전 비중 제로"라고 밝혔다.

    [카테고리]는 {keyword2}, [정치인 이름]은 {politician[1]}이야."""
                    summary = gpt(query).replace("'", "")

                    if not summary.startswith(f"[{keyword2}] {politician[1]}"):
                        print(f"Summary is wrong: {summary}")
                        continue
                    
                    query = f"""다음은 정치인의 정책 방향 요약입니다:
    {summary}

    이 내용을 기준으로 {keyword2}에서 {politician[1]}의 정치 성향은 다음 기준에 따라 몇 점인지 판단하세요:

    - 0.00: 매우 보수적
    - 0.50: 중도
    - 1.00: 매우 진보적

    0.00 부터 1.00 사이인 실수형 숫자를 알려줘. 형식은 무조건 숫자여야 해. 0.41이나 0.23이나 0.67같은 구체적인 숫자면 더욱 좋아."""
                    score = gpt(query)
                    
                    try:
                        sql = f"INSERT INTO stances (id_int, category_id, position_summary, position_score, source_url, id) VALUES (1, {keyword[0]}, '{summary}', {score}, '{article[1]}', '{politician[0]}')"
                        cur.execute(sql)
                    except Exception as e:
                        print(sql)
                        print("SQL EXECUTE ERROR")
                        print(e)
                    
                    print(f"{politician[1]}: {keyword[0]}, {keyword2}")
                    print(summary)
                    print(score)
                    print()
                
                con.commit()
                print("SAVED!")

def crawl_v2(category: str, start = 1, display = 100):
    url = f"https://openapi.naver.com/v1/search/news.json?query={category}&start={start}&display={display}&sort=sim"
    response = requests.get(url, headers={
        "Host": "openapi.naver.com",
        "User-Agent": "curl/7.49.1",
        "Accept": "*/*",
        "X-Naver-Client-Id": keys["NAVER_KEY_ID"],
        "X-Naver-Client-Secret": keys["NAVER_KEY_SECRET"]
    })
    articles = []
    
    if response.status_code != 200:
        return

    text_json = json.loads(response.text)
 
    for item in text_json["items"]:
        title: str = cleanhtml(item["title"])
        link: str = item["link"]
        description: str = cleanhtml(item["description"])
        description2 = get_article_naver(link)
        if description2 is not None:
            description2 = description2[1]
        else:
            description2 = ""

        if description2 == "":
            description2 = description

        articles.append((title, link, description, description2))

    return articles

def main():
    print("DB 자동화\n1. PostgreSQL 명령어 입력\n2. PostgreSQL 보기\n3. 크롤링")

    option_str = input("옵션을 선택하세요: ")
    option = int(option_str)

    if option == 1:
        execute()
    elif option == 2:
        view()
    elif option == 3:
        reverse_str = input("카테고리를 순차적으로 하실 거면 Y, 역행으로 하실 거면 N을 입력해주세요: ")
        start_from = input("어떤 정치인부터 시작할 건지 이름을 정해주세요 (공백 시 전체): ")
        reverse = False

        if reverse_str.lower() == "n":
            reverse = True

        crawl_all_v2(reverse, start_from)
        #crawl_all_articles()

main()

con.commit()
con.close()