import uuid
import datetime
import requests
import json
import re
import random
from openai import OpenAI
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.core.paginator import Paginator
from django.db.models import *
from django.db.models.functions import *
from .models import *

# Create your views here.
CLEANR = re.compile('<.*?>')

keys = {}
with open("../keys.json") as f:
    keys = json.load(f)
openai_client = OpenAI(api_key=keys["OPENAI_KEY"])

#region 1 메인 페이지
def index(request):
    redirect = request.GET.get('redirect')
    
    if redirect is not None:
        if redirect == 'home':
            return go_home(request)
        elif redirect == 'test':
            return on_test_click(request)
        else: # 외부 url
            return on_news_click(request, redirect)

    context = {}
    return render(request,'main/index.html', context)

def go_home(request):
    # 로고 버튼을 누르면 메인 홈페이지로 리다이렉트
    context = {}
    return render(request,'main/index.html', context)

def add_news_articles(request):
    # 뉴스 기사를 불러오고 (크롤링) post 데이터 (context)에 저장
    categories = ["정치", "경제", "글로벌", "사회"]
    context = {}

    for i in range(0, 4):
        category = categories[i]
        url = f"https://openapi.naver.com/v1/search/news.json?query={category}&start=1&display=3&sort=sim"
        response = requests.get(url, headers={
            "Host": "openapi.naver.com",
            "User-Agent": "curl/7.49.1",
            "Accept": "*/*",
            "X-Naver-Client-Id": keys["NAVER_KEY_ID"],
            "X-Naver-Client-Secret": keys["NAVER_KEY_SECRET"]
        })

        if response.status_code != 200:
            return

        text_json = json.loads(response.text)
        context[category] = []
    
        for item in text_json["items"]:
            title: str = re.sub(CLEANR, '', item["title"])
            link: str = item["link"]
            # description: str = re.sub(CLEANR, '', item["description"])

            article = {
                "title": title,
                "link": link
            }
            context[str(i)].append(article)

    return render(request, 'main/index.html', context)

def on_test_click(request):
    # 검사 버튼 클릭 시, 테스트 페이지로 리다이렉트
    context = {}
    return render(request, 'main/test.html', context)

def on_news_click(reqeust, button_name: str):
    # 뉴스 제목 클릭 시, 해당 뉴스 웹페이지로 리다이렉트, button_name -> redirect_url
    # <button type="submit" name="redirect_url" value="https://www.google.com">구글로 이동</button>
    return redirect(button_name)
#endregion




#region 2 질문 페이지
# 질문을 5개씩 보여주고, 응답을 저장하고, 마지막엔 결과 페이지로 이동
# 질문 페이지 인덱스 관리
#def PageIdxCtrl(request, page_num: int):
    #유효 인덱스 확인, 인덱스에 해당하는 질문 가져와 넘겨주기(기존 응답이 있다면 응답까지)
    #만약 인덱스가 유효 인덱스보다 커졌다면 결과분석페이지로 리다이렉트
    #응답값 저장 후, 이전/다음 url로 리다이렉트 => 응답값 저장하는 함수: SaveToCookie(), 참고로 그냥 Response()로 클래스 생성 후 SaveToCookie에서 DB 저장
    pass
#endregion
# def question_page(request, page_num):
#     QUESTIONS_PER_PAGE = 5
#     total_questions = Question.objects.count()
#     total_pages = (total_questions - 1) // QUESTIONS_PER_PAGE + 1

#     # 페이지 번호 유효성 검사
#     if page_num < 1 or page_num > total_pages:
#         return redirect('result_page')  # 결과 페이지로 이동

#     # 질문 가져오기
#     start = (page_num - 1) * QUESTIONS_PER_PAGE
#     end = start + QUESTIONS_PER_PAGE
#     questions = Question.objects.all()[start:end]

#     if request.method == 'POST':
#         for q in questions:
#             answer = request.POST.get(f'question_{q.id}')
#             if answer:
#                 Response.objects.update_or_create(
#                     user_id=request.session.session_key,
#                     question=q,
#                     defaults={'answer': answer}
#                 )
#         # 다음 페이지로 이동 또는 결과 페이지로 이동
#         if page_num < total_pages:
#             return redirect('question_page', page_num=page_num+1)
#         else:
#             return redirect('result_page')

#     # 기존 응답 불러오기(선택지 유지)
#     responses = {r.question_id: r.answer for r in Response.objects.filter(
#         user_id=request.session.session_key,
#         question__in=questions
#     )}

#     context = {
#         'questions': questions,
#         'page_num': page_num,
#         'total_pages': total_pages,
#         'responses': responses,
#     }
#     return render(request, 'main/question_page.html', context)
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib.sessions.models import Session
from django.utils import timezone
from .models import Question, Response, User
import uuid

def question_page(request, page_num):
    """
    설문 질문 페이지 - 5개씩 질문을 보여주고 응답을 저장
    """
    QUESTIONS_PER_PAGE = 5
    
    # 세션이 없으면 생성 (처음 방문하는 사용자)
    if not request.session.session_key:
        request.session.create()
    
    # 전체 질문 가져오기 (ID 순서대로)
    all_questions = Question.objects.all().order_by('id')
    
    # Django Paginator 사용 (더 안전하고 효율적)
    paginator = Paginator(all_questions, QUESTIONS_PER_PAGE)
    total_pages = paginator.num_pages
    
    # 페이지 번호 유효성 검사
    if page_num < 1:
        return redirect('question_page', page_num=1)
    elif page_num > total_pages:
        return redirect('result_page')  # 결과 페이지로 이동
    
    # 현재 페이지의 질문들 가져오기
    try:
        page_obj = paginator.get_page(page_num)
        questions = page_obj.object_list
    except:
        return redirect('question_page', page_num=1)
    
    # POST 요청 처리 (사용자가 답변을 제출했을 때)
    if request.method == 'POST':
        session_id = request.session.get('survey_session_id')
        
        # 설문 세션 ID가 없으면 새로 생성
        if not session_id:
            session_id = uuid.uuid4()
            request.session['survey_session_id'] = str(session_id)
        
        # 사용자 객체 가져오기 또는 생성
        user, created = User.objects.get_or_create(
            id=request.session.session_key,
            defaults={
                'tendency_vector': [0.5] * 10,  # 기본값
                'weight_vector': [1.0] * 10,    # 기본값
                'final_vector': [0.5] * 10,     # 기본값
            }
        )
        
        # 각 질문의 답변 저장
        for question in questions:
            answer = request.POST.get(f'question_{question.id}')
            if answer:
                try:
                    answer_int = int(answer)
                    if 1 <= answer_int <= 5:  # 유효한 답변인지 확인
                        # 기존 응답 업데이트 또는 새로 생성
                        Response.objects.update_or_create(
                            session_id=session_id,
                            user=user,
                            question=question,
                            defaults={
                                'answer': answer_int,
                                'tendency_score': 0.5,  # 기본값 (나중에 계산 로직 추가)
                                'survey_completed_at': timezone.now() if page_num == total_pages else None
                            }
                        )
                except ValueError:
                    continue  # 잘못된 답변은 무시
        
        # 다음 페이지로 이동 또는 결과 페이지로 이동
        if page_num < total_pages:
            return redirect('question_page', page_num=page_num + 1)
        else:
            # 마지막 페이지면 모든 응답의 완료 시간 업데이트
            Response.objects.filter(
                session_id=session_id,
                user=user
            ).update(survey_completed_at=timezone.now())
            return redirect('result_page')
    
    # 기존 응답 불러오기 (페이지를 다시 방문했을 때 선택 상태 유지)
    session_id = request.session.get('survey_session_id')
    responses = {}
    
    if session_id:
        existing_responses = Response.objects.filter(
            session_id=session_id,
            question__in=questions
        ).select_related('question')
        
        responses = {r.question.id: r.answer for r in existing_responses}
    
    # 템플릿에 전달할 데이터
    context = {
        'questions': questions,
        'page_num': page_num,
        'total_pages': total_pages,
        'responses': responses,
        'is_first_page': page_num == 1,  # 첫 페이지인지 확인
        'is_last_page': page_num == total_pages,  # 마지막 페이지인지 확인
        'prev_page': page_num - 1 if page_num > 1 else None,
        'next_page': page_num + 1 if page_num < total_pages else None,
    }
    
    return render(request, 'main/question_page.html', context)



#region 3 리포트 페이지
def result_page(request):
    # 유저의 대답을 기반으로 UI에 표시 후 렌더링
    responses = Response.objects.filter(user_id=get_user_id()).order_by('-survey_completed_at')
    responses2: list[Response] = [] # 가장 최근 진행한 유저의 대답 리스트
    created_at: DateTimeField = None

    for response in responses:
        if created_at is None:
            created_at = response.survey_completed_at
        if created_at == response.survey_completed_at:
            responses2.append(response)
        else:
            break

    # 구현 미완성
    

    return render(request, 'main/result.html')

def load_all_politicians() -> list[Politician]:
    # 국회의원 리스트를 DB에서 불러온 후 반환
    return Politician.objects.all()

def load_all_politicians_simple() -> list[PoliticianSimple]:
    # 국회의원의 기본 데이터 리스트를 DB에서 불러온 후 반환
    politicians = Politician.objects.values("id", "name", "hanja_name", "party_id", "birthdate", "address")
    politicians2 = []

    for politician in politicians:
        politician2 = PoliticianSimple()
        politician2.id = politician["id"]
        politician2.name = politician["name"]
        politician2.hanja_name = politician["hanja_name"]
        politician2.party_id = politician["party_id"]
        politician2.birthdate = politician["birthdate"]
        politician2.address = politician["address"]

        politicians2.append(politician2)
    
    return politician2

def load_politician(id: str) -> Politician:
    # 국회의원 ID를 기반으로 DB에서 불러온 후 반환
    return Politician.objects.get(id=id)

def load_all_parties() -> list[Party]:
    # 정당 리스트를 DB에서 불러온 후 반환
    return Politician.objects.all()

def write_report(responses: list[Response]):
    # 유저 응답이 담긴 리스트를 기반으로 분석
    # 유저의 리포트를 기반으로 정당과 정치인 적합도까지 점수화 후 해당 데이터 반환
    response = CreateResponse()
    pass

def on_report_item_hover(item_type: int, id: int | str):
    # item_type: 1 => 적합한 정당, 2 => 적합한 정치인 TOP, 3 => 적합한 정치인 WORST
    # id => 정치인 또는 정당 id
    # 랭킹 아이템을 갖다 댈시 그에 맞는 이유 표시
    pass
#endregion




#region 4 정치인 목록 페이지
def GoToPoliticianPage(request, int_id: int):
    #각 정치인 항목 클릭 시, str_id에 해당하는 정치인의 DB 데이터를 기반으로 랜더링
    politician = get_object_or_404(Politician, id=int_id)
    return render(request, 'main/politician_detail.html', {'politician': politician})

def FilteredInquiry(request):
    #사용자가 입력한 정당, 정치인 이름에 해당하는 요청에 따른 랜더링
    name_query = request.GET.get('name', '')
    party_query = request.GET.get('party', '')
    page_number = request.GET.get('page', 1)

    # 정치인 쿼리셋
    politicians = Politician.objects.all()
    if name_query:
        politicians = politicians.filter(name__icontains=name_query)
    if party_query:
        politicians = politicians.filter(party__name=party_query)

    paginator = Paginator(politicians, 30)
    page_obj = paginator.get_page(page_number)
    parties = Party.objects.all()

    context = {
        'page_obj': page_obj,
        'name_query': name_query,
        'party_query': party_query,
        'parties': parties,
    }
    return render(request, 'main/politician_list.html', context)

def Pagenation(request):
    #이전, 다음, 페이지 번호 수를 눌렀을 때, 해당 요청에 따른 랜더링
    pass
#endregion

#region 5 개별 집중 분석 페이지
def write_politician_report(id: str) -> Report:
    # 정치인의 분석 결과 반환
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

    return render(request,'main/politician_report.html',context)
  #endregion




#region 6 채팅 페이지
def GoToChat(request,str_id:str):
    #챗봇 상대의 해당하는 정치인 id를 받아, 해당 정치인의 성향 등을 반영한 정보를 기반으로 랜더링

    politician = load_politician(str_id)
    user_text = "" # 유저의 메시지는 어디서 가져올 것인가?

    # 정치인의 무슨 데이터를 반영할 것인지, 이 중에 필요 없는 정보는 무엇인지 제외 필요
    poly_infos = {
        '이름':politician.name,
        '한자명':politician.hanja_name,
        '영문명':politician.english_name,
        '직책':politician.job,
        '생일':politician.birthdate,
        '양력/음력':politician.birthdate_type,
        '선수':politician.reelected,
        '정당':politician.party,
        '성별':politician.gender,
        '위원회':politician.comittees or '위원회 없음',
        '주소':politician.address,
        '이메일':politician.email or '이메일 없음',
        '전화번호':politician.tel or '전화번호 없음',
        '경력':politician.profile,
        '저서':politician.book or '저서 없음',
        '현재 자산':politician.curr_assets,
        '보좌관':politician.boja,
        '수석비서관':politician.top_secretary,
        '비서':politician.secretary,
        '통과 법안':politician.bill_approved,
        '선거구명':politician.election_name,
        '선거구 구분':politician.election_type,
        '득표격차':politician.election_gap,
        '본회의 출석률':politician.attendance_plenary
    }
    response = ManageChat(request, user_text, politician, poly_infos)

    context = { "response": response }
    return render(request, "main/chat.html", context)

def ManageChat(request, user_text: str, politician: Politician, poly_infos: dict) -> str:
    #사용자의 메세지를 받아,정치인 스타일로 AI 응답 반환
    #응답 생성은 CreateResponse()호출로 이루어짐
    
    prompt = ""
    system = ""
    TONE_COUNT = 5

    speeches = Tone.objects.all()
    indicies = list(range(0, len(speeches)))
    speeches2: list[str] = [] # 최종 발언 데이터

    info1 = "" # 정치인 세부 정보
    info2 = "" # 정치인 말투

    random.shuffle(indicies)

    for i in range(0, TONE_COUNT):
        index = indicies[i]
        speech: Tone = speeches[index]
        speeches2.append(speech.speech)

    info1 = "\n".join([f"{key}: {poly_infos[key]}" for key in poly_infos])
    info2 = "\n\n".join(speeches2)
    system = f"""너의 임무는 지금부터 대한민국에서 정치 활동을 하고 있는 국회의원 {politician.name}이 되는 거야.
    {politician.name}, 기본 정보를 알려주자면 성별은 {politician.gender}, 생일은 {politician.birthdate}, 정당은 {politician.party}이고 경력은 '{politician.profile}'이야.
    
    다음 아래의 내용은 {politician.name}, 너의 개인 정보들이야.
    {info1}
    --------------------

    다음 아래의 내용은 {politician.name}, 너가 쓰는 말투가 들어가 있어. 너가 직접 문장 속 말투를 분석해서 그 말투를 기반으로 말해줘.
    {info2}
    --------------------
    
    넌 앞으로 성격, 말투, 외모, 지능 모두 {politician.name}인 척 말하고, 길게 말하지 마. 그리고 한국어로 말해."""
    prompt = user_text

    ai_text = CreateResponse(prompt, system) # 로직 구현 필요
    # 문제점: 텍스트만 생성해야 하고, 딴 질문에는 답변하지 않아야 함. 그런 제한할 수 있는 기능이 있나?

    return ai_text

def CreateResponse(prompt:str, system="")->str:
    #정치인 말투에 맞게 응답을 만들어내는 AI 호출
    messages = [{"role": "user", "content": prompt}]

    if system != "":
        messages.append({"role": "system", "content": system})

    completion = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    store=True,
    messages=messages
    )

    return completion.choices[0].message.content
#endreigon




#region 7 분야별 랭킹 페이지
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

    #null값 필드 지정정
    null_fields=['attendance','election_gap']

    #null값 뒤로 빼서 정렬
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



#region 8 지난 리포트 다시보기 페이지
def get_user_id(request):
    if request.COOKIES.get('id') is None:
        response = HttpResponse('SET USER ID')
        response.set_cookie('id', uuid.uuid4().hex)

    id = request.COOKIES.get('id')
    return id

def SaveToCookie(response,request,new_report):
    #새 리포트를 기존 쿠키에 누적 저장, response: list[Response], 2페이지에서 검사 다 하면 실행됨
    report: Report = write_report(response)
    report.save()

def ReportHistory(request):
    #쿠키에서 리포트 목록을 가져와 템플릿에 랜더링
    id = get_user_id()
    responses = Report.objects.filter(user_id=id)
    responses2: dict[list[Report]] = {}

    for response in responses:
        if responses2[response.created_at] is None:
            responses2[response.created_at] = []
        responses2[response.created_at].append(response)

    context = {
        "reports": []
    }
    i = 0

    for reports in responses2:
        if i >= 10: # limit
            break

        for report in reports:
            if i >= 10: # limit
                break

            context["reports"].append({
                "rank": i + 1,
                "date": report.created_at,
                "party": report.parties[0]["name"],
                "politician": report.politicians_top[0]["name"],
                "ratio": report.ratio
            })
            i += 1
    
    return render(request, 'history.html', context)
#endregion