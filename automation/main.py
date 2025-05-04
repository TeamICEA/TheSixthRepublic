import pymysql
import requests
from bs4 import BeautifulSoup

OPEN_KEY = ""
SQL_HOST = "175.205.96.45"
SQL_PORT = 3306
SQL_DATABASE = "republic"
SQL_USERNAME = "user"
SQL_PASSWORD = "teamicea211"

con = pymysql.connect(host=SQL_HOST, user=SQL_USERNAME, password=SQL_PASSWORD, database=SQL_DATABASE, port=SQL_PORT, use_unicode=True, charset='utf8')
cur = con.cursor()

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

def crawl():
    for i in range(1201498, 1211003):
    response = requests.get("https://theminjoo.kr/main/sub/news/view.php?sno=0&brd=230&post=1210973")

    if response.status_code == 200:
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        texts = soup.select_one("#container > div.article-body > div > div.board-view__wrap > div.board-view > div.board-view__body")
        print(texts.text)

def main():
    print("DB 자동화\n1. MySQL 명령어 입력\n2. MySQL 보기\n3. 크롤링링")

    option_str = input("옵션을 선택하세요: ")
    option = int(option_str)

    if option == 1:
        execute()
    elif option == 2:
        view()
    elif option == 3:
        crawl()

main()

con.commit()
con.close()