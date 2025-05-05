from django.shortcuts import render

# Create your views here.
context = {

}

def index(request):
    return render(request,'main/index.html', context)

#region 메인 페이지
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
def PageIdxCtrl(request,page_num):
    #유효 인덱스 확인, 인덱스에 해당하는 질문 가져와 넘겨주기(기존 응답이 있다면 응답까지)
    #만약 인덱스가 유효 인덱스보다 커졌다면 결과분석페이지로 리다이렉트
    #응답값 저장 후, 이전/다음 url로 리다이렉트
    pass

#정치인 목록 페이지
def GoToPoliticianPage(request,str_id):
    #str_id에 해당하는 정치인 데이터 기반으로 렌더링
    pass