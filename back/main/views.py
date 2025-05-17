from django.shortcuts import render, redirect
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




#region 질문페이지 인덱스 관리
#def PageIdxCtrl(request, page_num: int):
    #유효 인덱스 확인, 인덱스에 해당하는 질문 가져와 넘겨주기(기존 응답이 있다면 응답까지)
    #만약 인덱스가 유효 인덱스보다 커졌다면 결과분석페이지로 리다이렉트
    #응답값 저장 후, 이전/다음 url로 리다이렉트
    pass
#endregion
# 2 질문지 페이지: 질문을 5개씩 보여주고, 응답을 저장하고, 마지막엔 결과 페이지로 이동
def question_page(request, page_num):
    QUESTIONS_PER_PAGE = 5
    total_questions = Question.objects.count()
    total_pages = (total_questions - 1) // QUESTIONS_PER_PAGE + 1

    # 페이지 번호 유효성 검사
    if page_num < 1 or page_num > total_pages:
        return redirect('result_page')  # 결과 페이지로 이동

    # 질문 가져오기
    start = (page_num - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE
    questions = Question.objects.all()[start:end]

    if request.method == 'POST':
        for q in questions:
            answer = request.POST.get(f'question_{q.id}')
            if answer:
                Response.objects.update_or_create(
                    user_id=request.session.session_key,
                    question=q,
                    defaults={'answer': answer}
                )
        # 다음 페이지로 이동 또는 결과 페이지로 이동
        if page_num < total_pages:
            return redirect('question_page', page_num=page_num+1)
        else:
            return redirect('result_page')

    # 기존 응답 불러오기(선택지 유지)
    responses = {r.question_id: r.answer for r in Response.objects.filter(
        user_id=request.session.session_key,
        question__in=questions
    )}

    context = {
        'questions': questions,
        'page_num': page_num,
        'total_pages': total_pages,
        'responses': responses,
    }
    return render(request, 'main/question_page.html', context)



#region 리포트 페이지
def report_view(request):
    # 유저의 대답을 기반으로 UI에 표시 후 렌더링
    # return render(request, 'main/result.html')
    pass

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




#region 정치인 목록
def GoToPoliticianPage(request, str_id: str):
    #각 정치인 항목 클릭 시, str_id에 해당하는 정치인의 DB 데이터를 기반으로 랜더링
    pass

def FilteredInquiry(request):
    #사용자가 입력한 정당, 정치인 이름에 해당하는 요청에 따른 랜더링
    pass

def Pagenation(request):
    #이전, 다음, 페이지 번호 수를 눌렀을 때, 해당 요청에 따른 랜더링
    pass
#endregion




#region 개별 집중 분석
def preport_view(request, id: str):
    # 정치인 데이터를 DB에서 불러오는 함수와 분석 결과를 UI에 표시하는 함수를 호출한 후,
    # 나머지 데이터 렌더링링
    pass

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




#region 채팅 페이지
def GoToChat(request,str_id:str):
    #챗봇 상대의 해당하는 정치인 id를 받아, 해당 정치인의 성향 등을 반영한 정보를 기반으로 랜더링
    pass

def ManageChat(request, str_id:str):
    #사용자의 메세지를 받아,정치인 스타일로 AI 응답 반환
    #응답 생성은 CreateResponse()호출로 이루어짐
    pass

def CreateResponse(prompt:str)->str:
    #정치인 말투에 맞게 응답을 만들어내는 AI 호출
    pass
#endreigon




#region 분야별 랭킹
def GoToAnotherRanking(request,criteria:str):
    #사용자가 정렬 기준 항목 선택 시, 항목에 맞게 정렬된 DB 데이터를 기반으로 랜더링 
    pass

def GoToPoliticianPage(request, str_id: str):
    #각 정치인 항목 클릭 시, str_id에 해당하는 정치인의 DB 데이터를 기반으로 랜더링
    pass

def Pagenation(request):
    #이전, 다음, 페이지 번호 수를 눌렀을 때, 해당 요청에 따른 랜더링
    pass
#endregion



#region 지난 리포트 다시보기
def SaveToCookie(response,request,new_report):
    #새 리포트를 기존 쿠키에 누적 저장
    pass

def ReportHistory(request):
    #쿠키에서 리포트 목록을 가져와 템플릿에 랜더링
    pass
#endregion