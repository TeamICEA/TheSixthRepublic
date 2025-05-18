import psycopg2
import json
import csv

keys = {}
with open("keys.json") as f:
    keys = json.load(f)

con = psycopg2.connect(host=keys["SQL_HOST"], dbname=keys["SQL_DATABASE"],user=keys["SQL_USERNAME"],password=keys["SQL_PASSWORD"],port=5432)
cur = con.cursor()

def update_from_csv():
    FILE_NAME = "automation/politicians.csv"
    FIELD_NAMES = ["curr_assets", "bill_approved"]

    f = open(FILE_NAME, "r", encoding="utf-8")
    reader = csv.reader(f)
    start = False

    for row in reader:
        if not start:
            start = True
            continue
         
        id = row[0]
        values = [f"'{row[1]}'", f"'{row[2]}'"]
        fields = get_all_fields(FIELD_NAMES, values)

        query = f"UPDATE politicians SET {fields} WHERE id={id};"
        cur.execute(query)

def get_all_fields(names: list[str], values: list) -> str:
    fields = []

    for i in range(0, len(names)):
        fields.append(f"{names[i]} = {values[i]}")

    return ", ".join(fields)

print("DB 자동화 - 값 업데이트\n1. CSV로 업데이트")

option_str = input("옵션을 선택하세요: ")
option = int(option_str)

if option == 1:
    update_from_csv()

con.commit()
con.close()