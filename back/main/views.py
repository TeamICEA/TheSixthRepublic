from django.shortcuts import render
from .models import *

# Create your views here.
context = {

}

#region 메인 페이지
def index(request):
    return render(request,'main/index.html', context)

def go_home():
    # 로고 버튼을 누르면 메인 홈페이지로 리다이렉트
    pass

def add_news_articles():
    # 뉴스 기사를 불러오고 (크롤링) post 데이터 (context)에 저장
    pass

def on_test_click():
    # 검사 버튼 클릭 시, 테스트 페이지로 리다이렉트
    pass

def on_news_click(button_name: str):
    # 뉴스 제목 클릭 시, 해당 뉴스 웹페이지로 리다이렉트
    pass
#endregion

#질문페이지 인덱스 관리
def PageIdxCtrl(request, page_num: int):
    #유효 인덱스 확인, 인덱스에 해당하는 질문 가져와 넘겨주기(기존 응답이 있다면 응답까지)
    #만약 인덱스가 유효 인덱스보다 커졌다면 결과분석페이지로 리다이렉트
    #응답값 저장 후, 이전/다음 url로 리다이렉트
    pass

#region 리포트 페이지
def load_all_politicians() -> list[Politician]:
    # 국회의원 리스트를 DB에서 불러온 후 반환
    pass

def load_all_politicians_simple() -> list[PoliticianSimple]:
    # 국회의원의 기본 데이터 리스트를 DB에서 불러온 후 반환
    pass

def load_politician(id: str) -> Politician:
    # 국회의원 ID를 기반으로 DB에서 불러온 후 반환
    pass

def load_all_parties() -> list[Party]:
    # 정당 리스트를 DB에서 불러온 후 반환
    pass

def write_report(responses: list[Response]):
    # 유저 응답이 담긴 리스트를 기반으로 분석
    # 유저의 리포트를 기반으로 정당과 정치인 적합도까지 점수화
    pass

def on_report_item_hover(item_type: int, id: int | str):
    # item_type: 1 => 적합한 정당, 2 => 적합한 정치인 TOP, 3 => 적합한 정치인 WORST
    # id => 정치인 또는 정당당 id
    # 랭킹 아이템을 갖다 댈시 그에 맞는 이유 표시
    pass

#endregion

#region 정치인 목록 페이지
def GoToPoliticianPage(request, str_id: str):
    #str_id에 해당하는 정치인 데이터 기반으로 렌더링
    pass
#endregion

#region 개별 집중 분석
def add_politician_data(id: str):
    # 정치인 id를 기반으로 DB에서 데이터를 불러온 후 UI에 표시
    pass

def write_politician_report(id: str):
    # 정치인의 분석 결과를 UI에 표시
    pass

def on_preport_item_hover(item_type: int, id: str):
    # item_type: 1 => 적합한 정치인 TOP, 2 => 적합한 정치인 WORST
    # id => 정치인 id
    # 랭킹 아이템을 갖다 댈시 그에 맞는 이유 표시
    pass
#endregion