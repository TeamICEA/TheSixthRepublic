import uuid
import datetime
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import *
from django.db.models.functions import *
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
def PageIdxCtrl(request, page_num: int):
    #유효 인덱스 확인, 인덱스에 해당하는 질문 가져와 넘겨주기(기존 응답이 있다면 응답까지)
    #만약 인덱스가 유효 인덱스보다 커졌다면 결과분석페이지로 리다이렉트
    #응답값 저장 후, 이전/다음 url로 리다이렉트
    pass
#endregion




#region 리포트 페이지
def report_view(request):
    # 유저의 대답을 기반으로 UI에 표시 후 렌더링
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

def write_report(responses: list[Responses]):
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
def write_politician_report(id: str):
    # 정치인의 분석 결과를 UI에 표시
    pass

def on_preport_item_hover(item_type: int, id: str):
    # item_type: 1 => 적합한 정치인 TOP, 2 => 적합한 정치인 WORST
    # id => 정치인 id
    # 랭킹 아이템을 갖다 댈시 그에 맞는 이유 표시
    pass



def IndividualPoliticians(request, str_id):

    politician=get_object_or_404(Politician,str_id=str_id)
    #str_id와 같은 아이디, Politician에서 갖고오기
    report=write_politician_report(str_id)
    #도우미함수 호출(리포트 작성 완성이 우선)
    best_rank=on_report_item_hover(1,str_id)
    wort_rank=on_report_item_hover(2,str_id)
    #랭킹 데이터
    context={
        'name':politician.name,
        'hanja':politician.hanja_name,
        'eng':politician.english_name,
        'job':politician.job,
        'birth':politician.birthdate,
        'birth_type':politician.birthdate_type,
        'reelected':politician.reelected,
        'party':politician.party,
        'gender':politician.gender,
        'comittees':politician.comittees or '위원회 없음',
        'address':politician.address,
        'email':politician.email or '이메일 없음',
        'tel':politician.tel or '전화번호 없음',
        'profile':politician.profile,
        'pic':politician.pic_link,
        'book':politician.book or '저서 없음',
        'curr_assets':politician.curr_assets,
        'boja':politician.boja,
        'top_secretary':politician.top_secretary,
        'secretary':politician.secretatry,
        'bill_approved':politician.bill_approved,
        'election_name':politician.election_name,
        'election_type':politician.election_type,
        'politician_report':report,
        'best_rank':best_rank,
        "worst_rank":wort_rank
    }

    return render(request,'politician_report.html',context)#endregion




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
def PoliticianRanking(request):

    sort_by=request.GET.get('sort','reelected')


    #나이 계산을 위한 변수 current_year
    current_year=datetime.date.today().year

    politicians=Politician.objects.annotate(

        #다선 여부 가공
        reelected_count=Case(
            When(reelected='초선',then=Value(1)),
            When(reelected='재선',then=Value(2)),
            When(reelected='3선',then=Value(3)),
            When(reelected='4선',then=Value(4)),
            When(reelected='5선',then=Value(5)),
            When(reelected='6선',then=Value(6)),
            default=Value(0),
            output_field=IntegerField()
        ),
    
    #나이 가공
        age=ExpressionWrapper(
            Value(current_year)-ExtractYear('birthdate'),
            output_field=IntegerField()
        )
    )

    #정렬 기준 설정(정렬 필드)
    sort_fields={
        'reelected':'-reelected_count',
        'curr_assets':'-curr_assets',
        'birthdate':'-age',
        'attendance':'-attendance_plenary',
        'election_gap':'-election_gap',
    }

    #기본 정렬 기준 설정(다선여부)
    standard_order_field=sort_fields.get(sort_by,'-reelected_count')

    #null값 뒤로 빼서 정렬
    null_fields=['attendance','election_gap']

    if any(key in sort_by for key in null_fields):
        if(standard_order_field.startswith('-')):
            field=F(standard_order_field[1:]).desc(nulls_last=True)
        else:
            field=F(standard_order_field).asc(nulls_last=True)
        politicians=politicians.order_by(field)
    else:
        politicians=politicians.order_by(standard_order_field)

    #페이지네이션
    paginator=Paginator(politicians,20)
    page_num=request.GET.get('page')
    page_obj=paginator.get_page(page_num)

    #넘겨줄 정보 만들기
    context={
        'politicians':page_obj,
        'sort_by':sort_by
    }

    return render(request,'politician_ranking.html',context)
#endregion



#region 지난 리포트 다시보기
def SaveToCookie(response,request,new_report):
    if request.COOKIES.get('id') is None:
        response.set_cookie('id', uuid.uuid4().hex)
    id = request.COOKIES.get('id')

    # TODO: 질문별 for문 돌려서 완성
    for i in range(0, 100):
        response = Responses.objects.create(user_id=id, question_id=0, answer=0, answer_text="", response_date=datetime.datetime.now(), position_score=0)
        # response.save()

    # 대충 uuid를 쿠키에서 불러오고 DB에 응답 저장!!!!!!!!!!!!!!!!!!!
    #새 리포트를 기존 쿠키에 누적 저장
    pass

def ReportHistory(request):
    id = request.COOKIES.get('id')

    if id is None:
        pass # 오류: uuid가 존재하지 않음

    responses = Responses.objects.filter(user_id=id)

    for response in responses:
        pass

    # uuid를 쿠키에서 가져오고 DB에서 불러온 뒤 렌더링합시다!!!!!!!!!!!!!!
    #쿠키에서 리포트 목록을 가져와 템플릿에 랜더링
    pass
#endregion