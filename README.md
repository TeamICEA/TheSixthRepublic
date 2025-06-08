# The 6th Republic
![logo](https://avatars.githubusercontent.com/u/207436724?s=300&v=4)
![intro](https://github.com/TeamICEA/TheSixthRepublic/blob/main/intro.jpg?raw=true)
 > [!NOTE]
 > 정치 성향 분석 서비스
>
Discover where you stand.

> 팀아아 제작

## 개요
주요 기능
1. 정치 성향 분석 리포트 제공
2. 국회의원 데이터로 학습한 챗봇 서비스 제공 (웹 크롤링하여 데이터 수집)
3. 국회의원별 정보 통계 사이트 (항목별 랭킹, 상세정보 등등)

## 구조
- [automation](https://github.com/TeamICEA/TheSixthRepublic/tree/main/automation): DB 관련 자동화 툴
- [back](https://github.com/TeamICEA/TheSixthRepublic/tree/main/back): 백엔드 (Django)

## 사용법
```json
{
    "OPENAI_KEY": "KEY1",
    "OPENAPI_KEY": "KEY2",
    "DJANGO_KEY": "KEY3",
    "SQL_HOST": "localhost",
    "SQL_DATABASE": "DATABASE_NAME",
    "SQL_USERNAME": "USER_NAME",
    "SQL_PASSWORD": "USER_PASSWORD",
    "NAVER_KEY_ID": "KEY4",
    "NAVER_KEY_SECRET": "KEY5"
}
```
1. `keys.json`을 루트 디렉터리 내에 생성하셔서 내용을 API KEY에 맞춰 넣어주세요.

```
pip install -r requirements.txt
```
2. 위 명령어로 필요한 패키지를 설치해주세요.

3. Django를 이용하실 경우 `back` 디렉터리가 현재 작업 디렉터리가 되도록 해주세요.

## 크레딧
- 충북대학교 내 '**오픈소스 기초 프로젝트**' 수업의 프로젝트입니다.
