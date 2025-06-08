import uuid
import datetime
import requests
import json
import re
import random
from datetime import timedelta
from openai import OpenAI
from google import genai
from google.genai import types
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
from django.db.models import *
from django.db.models.functions import *
from .models import *
from .utils import process_survey_completion
from django.http import Http404

# Create your views here.
CLEANR = re.compile('<.*?>')

keys = {}
with open("../keys.json") as f:
    keys = json.load(f)
openai_client = OpenAI(api_key=keys["OPENAI_KEY"])
gemini_client = genai.Client(api_key=keys["GEMINI_KEY"])

def get_user_id(request):
    """세션에서 사용자 UUID 가져오기"""
    print("🔍 get_user_id 함수 시작")
    try:
        if not request.session.session_key:
            print("🔑 세션 키가 없어서 새로 생성")
            request.session.create()
        
        user_uuid = request.session.get('user_uuid')
        print(f"🔍 세션에서 가져온 user_uuid: {user_uuid}")
        return user_uuid
    except Exception as e:
        print(f"❌ get_user_id 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def smart_survey_redirect(request):
    """
    베너의 '성향분석 리포트 보기' 버튼 클릭 시 상황에 따른 스마트 리다이렉트
    
    1. 지난 설문이 존재하면 → 8페이지 지난 리포트 다시보기
    2. 지난 설문이 없고 중단된 설문조사가 있으면 → 설문 이어서하기
    3. 아무것도 없으면 → 설문 시작하기
    """
    try:
        # 1. 사용자 UUID 처리
        user_uuid = get_user_id(request)
        
        if not user_uuid:
            # 새 사용자면 설문 시작
            new_user = User.objects.create()
            user_uuid = str(new_user.id)
            request.session['user_uuid'] = user_uuid
            print(f"새 사용자 생성: {user_uuid} → 설문 시작")
            return redirect('question_page', page_num=1)
        
        try:
            current_user = User.objects.get(id=user_uuid)
        except User.DoesNotExist:
            # 유효하지 않은 UUID면 새로 생성
            new_user = User.objects.create()
            user_uuid = str(new_user.id)
            request.session['user_uuid'] = user_uuid
            current_user = new_user
            print(f"사용자 재생성: {user_uuid} → 설문 시작")
            return redirect('question_page', page_num=1)
        
        # 2. 완료된 리포트가 있는지 확인 (가장 최신)
        completed_reports = UserReport.objects.filter(
            user=current_user
        ).order_by('-created_at')
        
        if completed_reports.exists():
            # 지난 설문이 존재하면 8페이지 지난 리포트 다시보기로 이동
            print(f"사용자 {user_uuid} → 8페이지 지난 리포트 다시보기")
            return redirect('history')
        
        # 3. 진행 중인 설문이 있는지 확인
        incomplete_responses = Response.objects.filter(
            user=current_user,
            survey_completed_at__isnull=True
        ).order_by('-id')
        
        if incomplete_responses.exists():
            # 진행 중인 설문이 있으면 이어서하기
            # 세션에 설문 ID 설정
            first_response = incomplete_responses.first()
            request.session['current_survey_session_id'] = str(first_response.survey_attempt_id)
            
            # 답변하지 않은 첫 번째 질문 찾기
            answered_question_ids = incomplete_responses.values_list('question_id', flat=True)
            all_question_ids = list(Question.objects.values_list('id', flat=True).order_by('id'))
            
            next_unanswered_question = None
            for q_id in all_question_ids:
                if q_id not in answered_question_ids:
                    next_unanswered_question = q_id
                    break
            
            if next_unanswered_question:
                # 다음 답변할 질문이 속한 페이지 계산
                next_page = ((next_unanswered_question - 1) // 5) + 1
                print(f"사용자 {user_uuid} → 설문 이어서하기 (페이지 {next_page})")
                return redirect('question_page', page_num=next_page)
            else:
                # 모든 질문에 답했는데 완료 처리가 안 된 경우 → 결과 페이지
                print(f"사용자 {user_uuid} → 결과 페이지로 이동")
                return redirect('user_report')
        
        # 4. 아무것도 없으면 새로운 설문 시작
        print(f"사용자 {user_uuid} → 새 설문 시작")
        return redirect('question_page', page_num=1)
        
    except Exception as e:
        print(f"스마트 리다이렉트 오류: {e}")
        # 오류 시 기본적으로 설문 시작
        return redirect('question_page', page_num=1)


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

    return add_news_articles(request)

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
        context[str(i)] = []
    
        for item in text_json["items"]:
            title: str = re.sub(CLEANR, '', item["title"]).replace("&quot;", '"').replace("&amp;", "&")
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
def get_existing_responses(current_survey_session, current_user, questions):
    """기존 응답 불러오기"""
    print(f"📖 get_existing_responses 시작: session={current_survey_session}, user={current_user}")
    
    responses = {}
    responses_text = {}
    
    if current_survey_session and current_user:
        try:
            existing_responses = Response.objects.filter(
                survey_attempt_id=current_survey_session,
                user=current_user,
                question__in=questions
            )
            
            print(f"📖 기존 응답 쿼리 결과: {existing_responses.count()}개")
            
            for response in existing_responses:
                responses[response.question.id] = response.answer
                if response.answer_text:
                    responses_text[response.question.id] = response.answer_text
                print(f"📖 응답 로드: 질문{response.question.id} = {response.answer}")
                    
        except Exception as e:
            print(f"❌ 기존 응답 조회 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"📖 최종 응답 수: responses={len(responses)}, responses_text={len(responses_text)}")
    return responses, responses_text


def question_page(request, page_num):
    """
    설문 질문 페이지 - 5개씩 질문을 보여주고 응답을 저장
    """
    QUESTIONS_PER_PAGE = 5
    
    try:
        # 1. 사용자 UUID 처리
        user_uuid = get_user_id(request)
        
        if not user_uuid:
            # User 모델은 UUID만 가지는 단순한 모델
            new_user = User.objects.create()
            user_uuid = str(new_user.id)
            request.session['user_uuid'] = user_uuid
        
        # 2. User 객체 가져오기 (예외 처리 추가)
        try:
            current_user = User.objects.get(id=user_uuid)
        except User.DoesNotExist:
            # 세션에 있는 UUID가 유효하지 않은 경우 새로 생성
            new_user = User.objects.create()
            user_uuid = str(new_user.id)
            request.session['user_uuid'] = user_uuid
            current_user = new_user
        
        # 3. 카테고리 확인
        categories = Category.objects.all()
        if not categories.exists():
            return render(request, 'main/error.html', {
                'error_message': '설문 카테고리가 없습니다.'
            })
        
        # 4. 질문 데이터 처리
        all_questions = Question.objects.all().order_by('id')
        if not all_questions.exists():
            return render(request, 'main/error.html', {
                'error_message': '설문 질문이 없습니다.'
            })
        
        # 5. Django Paginator로 페이지 나누기
        paginator = Paginator(all_questions, QUESTIONS_PER_PAGE)
        total_pages = paginator.num_pages
        
        # 6. 진행률 계산
        progress_percentage = (page_num / total_pages) * 100
        
        # 7. 페이지 번호 유효성 검사
        if page_num < 1:
            return redirect('question_page', page_num=1)
        elif page_num > total_pages:
            return redirect('user_report')
        
        # 8. 현재 페이지의 질문들 가져오기
        try:
            page_obj = paginator.get_page(page_num)
            questions = page_obj.object_list
        except:
            return redirect('question_page', page_num=1)
        
        # 9. 진행 중인 설문의 survey_attempt_id 확인
        current_survey_session = request.session.get('current_survey_session_id')
        
        # 10. 진행 중인 설문이 있고, GET 요청이면 적절한 페이지로 리다이렉트
        if current_survey_session and request.method == 'GET':
            # 답변하지 않은 첫 번째 질문 찾기
            answered_questions = Response.objects.filter(
                survey_attempt_id=current_survey_session,
                user=current_user,
                survey_completed_at__isnull=True
            ).values_list('question_id', flat=True)
            
            if answered_questions:
                # 모든 질문 ID 가져오기
                all_question_ids = list(Question.objects.values_list('id', flat=True).order_by('id'))
                
                # 답변하지 않은 첫 번째 질문 찾기
                next_unanswered_question = None
                for q_id in all_question_ids:
                    if q_id not in answered_questions:
                        next_unanswered_question = q_id
                        break
                
                if next_unanswered_question:
                    next_page = ((next_unanswered_question - 1) // QUESTIONS_PER_PAGE) + 1
                    #region 이 부분 수정(석환)
                    if page_num > next_page:
                        return redirect('question_page', page_num=next_page)
                    #endregion

                    
        # 11. POST 요청 처리 (사용자가 답변을 제출했을 때)
        if request.method == 'POST':
            # 12. 필수 답변 검사
            missing_answers = []
            for question in questions:
                answer = request.POST.get(f'question_{question.id}')
                if not answer:  # 객관식 답변이 없으면
                    missing_answers.append(question.id)
            
            if missing_answers:
                # 오류가 있으면 현재 페이지 다시 표시
                responses, responses_text = get_existing_responses(
                    current_survey_session, current_user, questions
                )
                
                # 미리 처리된 데이터 생성 (오류 상황)
                questions_with_data = []
                for q in questions:
                    questions_with_data.append({
                        'question': q,
                        'current_answer': responses.get(q.id),
                        'current_text': responses_text.get(q.id, ''),
                        'has_error': q.id in missing_answers,
                    })
                
                context = {
                    'questions_with_data': questions_with_data,
                    'page_num': page_num,
                    'total_pages': total_pages,
                    'progress_percentage': progress_percentage,
                    'is_first_page': page_num == 1,
                    'is_last_page': page_num == total_pages,
                    'prev_page': page_num - 1 if page_num > 1 else None,
                    'next_page': page_num + 1 if page_num < total_pages else None,
                    'answer_choices': Response.ANSWER_CHOICES,
                    'error_message': '모든 질문에 답변해주세요.',
                    'missing_questions': missing_answers,
                }
                return render(request, 'main/question_page.html', context)
            
            # 13. 진행 중인 설문 session_id가 없으면 새로 생성 또는 기존 것 찾기
            if not current_survey_session:
                # 기존 미완료 응답이 있는지 확인
                existing_incomplete = Response.objects.filter(
                    user=current_user,
                    survey_completed_at__isnull=True
                ).first()
                
                if existing_incomplete:
                    # 기존 미완료 설문이 있으면 그 survey_attempt_id 사용
                    current_survey_session = existing_incomplete.survey_attempt_id
                    request.session['current_survey_session_id'] = str(current_survey_session)
                else:
                    # 완전히 새로운 설문 시작
                    current_survey_session = uuid.uuid4()
                    request.session['current_survey_session_id'] = str(current_survey_session)
            
            # 14. 각 질문의 답변 저장 (최적화된 방식)
            with transaction.atomic():
                responses_to_create = []
                responses_to_update = []
                
                for question in questions:
                    answer = request.POST.get(f'question_{question.id}')
                    answer_text = request.POST.get(f'question_text_{question.id}')
                    
                    if answer:
                        try:
                            answer_int = int(answer)
                            if 1 <= answer_int <= 5:
                                # 기존 응답 확인
                                existing_response = Response.objects.filter(
                                    survey_attempt_id=current_survey_session,
                                    user=current_user,
                                    question=question
                                ).first()
                                
                                if existing_response:
                                    existing_response.answer = answer_int
                                    if answer_text and answer_text.strip():
                                        existing_response.answer_text = answer_text.strip()
                                    responses_to_update.append(existing_response)
                                else:
                                    new_response = Response(
                                        survey_attempt_id=current_survey_session,
                                        user=current_user,
                                        question=question,
                                        answer=answer_int,
                                        answer_text=answer_text.strip() if answer_text and answer_text.strip() else ''
                                    )
                                    responses_to_create.append(new_response)
                        except ValueError:
                            continue
                
                # 벌크 저장
                if responses_to_create:
                    Response.objects.bulk_create(responses_to_create)
                if responses_to_update:
                    Response.objects.bulk_update(responses_to_update, ['answer', 'answer_text'])
            
            # 15. 페이지 이동 처리
            if page_num < total_pages:
                return redirect('question_page', page_num=page_num + 1)
            else:
                # 설문 완료 처리
                # 1. 모든 응답에 완료 시각 설정
                Response.objects.filter(
                    survey_attempt_id=current_survey_session,
                    user=current_user
                ).update(survey_completed_at=timezone.now())
                
                # 2. 4-3 함수 호출 - 사용자 벡터 계산 + 보고서 생성
                result = process_survey_completion(
                    current_survey_session, 
                    current_user.id
                )
                
                if result['success']:
                    print(f"사용자 보고서 생성 완료: UserReport ID {result['user_report_id']}")
                else:
                    print(f"보고서 생성 실패: {result['error_message']}")
                
                # 3. 세션 정리
                if 'current_survey_session_id' in request.session:
                    del request.session['current_survey_session_id']
                
                return redirect('user_report')
        
        # 16. GET 요청 처리 - 기존 응답 불러오기
        responses, responses_text = get_existing_responses(
            current_survey_session, current_user, questions
        )
        
        # 17. 미리 처리된 데이터 생성 (정상 상황)
        questions_with_data = []
        for q in questions:
            questions_with_data.append({
                'question': q,
                'current_answer': responses.get(q.id),
                'current_text': responses_text.get(q.id, ''),
                'has_error': False,
            })
        
        context = {
            'questions_with_data': questions_with_data,
            'page_num': page_num,
            'total_pages': total_pages,
            'progress_percentage': progress_percentage,
            'is_first_page': page_num == 1,
            'is_last_page': page_num == total_pages,
            'prev_page': page_num - 1 if page_num > 1 else None,
            'next_page': page_num + 1 if page_num < total_pages else None,
            'answer_choices': Response.ANSWER_CHOICES,
        }
        
        return render(request, 'main/question_page.html', context)
        
    except Exception as e:
        print(f"question_page 오류: {e}")
        return render(request, 'main/error.html', {
            'error_message': '시스템 오류가 발생했습니다.'
        })




#region 3 리포트 페이지
# def result_page(request):
#     # 유저의 대답을 기반으로 UI에 표시 후 렌더링
#     responses = Response.objects.filter(user_id=get_user_id(request)).order_by('-survey_completed_at')
#     responses2: list[Response] = [] # 가장 최근 진행한 유저의 대답 리스트
#     created_at: DateTimeField = None

#     for response in responses:
#         if created_at is None:
#             created_at = response.survey_completed_at
#         if created_at == response.survey_completed_at:
#             responses2.append(response)
#         else:
#             break

#     # 구현 미완성
    

#     return render(request, 'main/result.html')

# def load_all_politicians() -> list[Politician]:
#     # 국회의원 리스트를 DB에서 불러온 후 반환
#     return Politician.objects.all()

# def load_all_politicians_simple() -> list[PoliticianSimple]:
#     # 국회의원의 기본 데이터 리스트를 DB에서 불러온 후 반환
#     politicians = Politician.objects.values("id", "name", "hanja_name", "party_id", "birthdate", "address")
#     politicians2 = []

#     for politician in politicians:
#         politician2 = PoliticianSimple()
#         politician2.id = politician["id"]
#         politician2.name = politician["name"]
#         politician2.hanja_name = politician["hanja_name"]
#         politician2.party_id = politician["party_id"]
#         politician2.birthdate = politician["birthdate"]
#         politician2.address = politician["address"]

#         politicians2.append(politician2)
    
#     return politician2

# def load_politician(id: str) -> Politician:
#     # 국회의원 ID를 기반으로 DB에서 불러온 후 반환
#     return Politician.objects.get(id=id)

# def load_all_parties() -> list[Party]:
#     # 정당 리스트를 DB에서 불러온 후 반환
#     return Politician.objects.all()

# def write_report(responses: list[Response]):
#     # 유저 응답이 담긴 리스트를 기반으로 분석
#     # 유저의 리포트를 기반으로 정당과 정치인 적합도까지 점수화 후 해당 데이터 반환
#     response = CreateResponse()
#     pass

# def on_report_item_hover(item_type: int, id: int | str):
#     # item_type: 1 => 적합한 정당, 2 => 적합한 정치인 TOP, 3 => 적합한 정치인 WORST
#     # id => 정치인 또는 정당 id
#     # 랭킹 아이템을 갖다 댈시 그에 맞는 이유 표시
#     pass
# #endregion


#region 3 리포트 페이지 (석환)
# def ShowUserReport(request):
#     date = request.GET.get('date')
#     user_id = get_user_id(request)

#     if date is not None:
#         report = UserReport.objects.filter(user=user_id, created_at__gte=date).order_by("created_at").first()
#         return ShowUserReportBy(request, report)

#     latest_report=UserReport.objects.filter(user=user_id).order_by("-created_at").first()
#     return ShowUserReportBy(request, latest_report)
    
# def ShowUserReportBy(request, latest_report: UserReport):
#     if latest_report is None:
#         raise Http404("None report")

#     context={
#         'report':latest_report.full_text,
#         'parties_rank':latest_report.parties_rank,
#         'politicians_top':latest_report.politicians_top,
#         'politicians_bottom':latest_report.politicians_bottom,
#     }
#     return render(request,'main/user_report.html',context)

def ShowUserReport(request):
    """사용자 보고서 표시 - 디버깅 코드 포함"""
    print("🔍 ShowUserReport 함수 시작")
    
    date = request.GET.get('date')
    user_uuid = get_user_id(request)
    print(f"🔍 user_uuid: {user_uuid}")
    print(f"🔍 date 파라미터: {date}")
    
    if not user_uuid:
        print("❌ user_uuid가 없음 - 설문 페이지로 리다이렉트")
        return redirect('question_page', page_num=1)
    
    try:
        current_user = User.objects.get(id=user_uuid)
        print(f"✅ User 객체 찾음: {current_user} (ID: {current_user.id})")
    except User.DoesNotExist:
        print(f"❌ User 객체를 찾을 수 없음 - UUID: {user_uuid}")
        return redirect('question_page', page_num=1)
    except Exception as e:
        print(f"❌ User 조회 중 오류: {e}")
        return redirect('question_page', page_num=1)

    # 날짜 기반 조회
    if date is not None:
        print(f"📅 날짜 기반 조회: {date}")
        try:
            report = UserReport.objects.filter(
                user=current_user, 
                created_at__gte=date
            ).order_by("created_at").first()
            print(f"📊 날짜 기반 리포트 결과: {report}")
            return ShowUserReportBy(request, report)
        except Exception as e:
            print(f"❌ 날짜 기반 조회 오류: {e}")

    # 최신 리포트 조회
    print("📊 최신 리포트 조회 시작")
    try:
        latest_report = UserReport.objects.filter(
            user=current_user
        ).order_by("-created_at").first()
        print(f"📊 최신 리포트 결과: {latest_report}")
        
        if latest_report:
            print(f"✅ 리포트 발견:")
            print(f"  - ID: {latest_report.id}")
            print(f"  - 생성일: {latest_report.created_at}")
            print(f"  - 사용자: {latest_report.user}")
            print(f"  - full_text 길이: {len(latest_report.full_text) if latest_report.full_text else 0}")
            print(f"  - parties_rank 개수: {len(latest_report.parties_rank) if latest_report.parties_rank else 0}")
            print(f"  - politicians_top 개수: {len(latest_report.politicians_top) if latest_report.politicians_top else 0}")
        else:
            print("❌ 리포트가 없음 - 설문 페이지로 리다이렉트")
            return redirect('question_page', page_num=1)
            
    except Exception as e:
        print(f"❌ 최신 리포트 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return redirect('question_page', page_num=1)
        
    return ShowUserReportBy(request, latest_report)

def ShowUserReportBy(request, latest_report: UserReport):
    """특정 UserReport 객체로 보고서 표시 - 디버깅 코드 포함"""
    print("🔍 ShowUserReportBy 함수 시작")
    print(f"📊 전달받은 리포트: {latest_report}")
    
    if latest_report is None:
        print("❌ latest_report가 None - 404 처리")
        raise Http404("리포트를 찾을 수 없습니다")
    
    try:
        # 리포트 데이터 상세 검증
        print("🔍 리포트 데이터 검증 시작:")
        
        full_text = latest_report.full_text
        print(f"  - full_text: {type(full_text)}, 길이: {len(full_text) if full_text else 0}")
        
        parties_rank = latest_report.parties_rank
        print(f"  - parties_rank: {type(parties_rank)}, 개수: {len(parties_rank) if parties_rank else 0}")
        
        politicians_top = latest_report.politicians_top
        print(f"  - politicians_top: {type(politicians_top)}, 개수: {len(politicians_top) if politicians_top else 0}")
        
        politicians_bottom = latest_report.politicians_bottom
        print(f"  - politicians_bottom: {type(politicians_bottom)}, 개수: {len(politicians_bottom) if politicians_bottom else 0}")
        
        # 각 데이터의 샘플 출력
        if full_text:
            print(f"  - full_text 샘플: {full_text[:100]}...")
        
        if parties_rank and len(parties_rank) > 0:
            print(f"  - parties_rank 첫 번째 항목: {parties_rank[0]}")
        
        if politicians_top and len(politicians_top) > 0:
            print(f"  - politicians_top 첫 번째 항목: {politicians_top[0]}")
        
        # 컨텍스트 구성
        context = {
            'report': full_text,
            'parties_rank': parties_rank,
            'politicians_top': politicians_top,
            'politicians_bottom': politicians_bottom,
        }
        
        print("✅ 컨텍스트 구성 완료")
        print(f"🎯 템플릿 렌더링: main/user_report.html")
        
        return render(request, 'main/user_report.html', context)
        
    except Exception as e:
        print(f"❌ ShowUserReportBy 오류: {e}")
        import traceback
        traceback.print_exc()
        raise Http404("리포트 처리 중 오류가 발생했습니다")
#endregion


def politician_detail(request, politician_id: int): # 이 함수 뭐임? 5페이지 함수 아닌가?
    """개별 정치인 상세 페이지"""
    # select_related로 정당 정보도 함께 가져와서 쿼리 최적화
    politician = get_object_or_404(
        Politician.objects.select_related('party'), 
        id=politician_id
    )
    
    context = {
        'politician': politician,
    }
    return render(request, 'main/politician_detail.html', context)


#region 4 정치인 목록 페이지
def politician_list(request):
    """정치인 목록 페이지 (검색 및 필터링 포함)"""
    # GET 파라미터 받기
    name_query = request.GET.get('name', '').strip()
    party_query = request.GET.get('party', '').strip()
    page_number = request.GET.get('page', 1)
    
    # 기본 쿼리셋 (정당 정보도 함께 가져오기)
    politicians = Politician.objects.select_related('party').all()
    
    # 이름 검색 (검색창 입력)
    if name_query:
        politicians = politicians.filter(name__icontains=name_query)
    
    # 정당 필터링 (9개 버튼 클릭)
    if party_query:
        try:
            politicians = politicians.filter(party_id=int(party_query))
        except ValueError:
            # 잘못된 정당 ID 무시
            pass
    
    # 가나다순 정렬
    politicians = politicians.order_by('name')
    
    # 페이지네이션
    paginator = Paginator(politicians, 20) # 한 페이지당 20명
    page_obj = paginator.get_page(page_number)
    
    # 정당 목록 (무소속 포함 8개, 버튼은 총 9개)
    # 0: 무소속, 1~7: 원내 정당들 - ID 기준으로 가져오기
    parties_for_buttons = Party.objects.filter(
        id__in=[0, 1, 2, 3, 4, 5, 6, 7] # 무소속 포함 8개 정당
    ).order_by('id')
    
    # 선택된 정당 이름 계산
    selected_party_name = "정당"
    if party_query:
        try:
            selected_party = Party.objects.get(id=int(party_query))
            selected_party_name = selected_party.name
        except (Party.DoesNotExist, ValueError):
            selected_party_name = "정당"

    context = {
        'page_obj': page_obj,
        'name_query': name_query,
        'party_query': party_query,
        'parties_for_buttons': parties_for_buttons,  # 9개 버튼용
        'selected_party_name': selected_party_name, 
        'total_count': politicians.count(),
    }
    return render(request, 'main/politician_list.html', context)
#endregion

#region 5 개별 집중 분석 페이지

# 정치인의 분석 결과 반환(해당하는 str_id 맞춰서 보고서 반환)
def load_politician_report(id: str): #-> Report

    #5의 메인 함수 파라미터 이용해서 politician 데이터 불러오기
    politician=get_object_or_404(Politician,str_id=id)

    #외래키 이용해서 PoliticianReport 테이블에서 일치하는 값 최신순 하나 가져오기
    politician_report = PoliticianReport.objects.filter(politician_id=politician.id).order_by('-created_at')

    #없다면 None Report 출력
    if not politician_report.exists():
        raise Http404("None Report")
    
    return politician_report.first().full_text.replace("**", "").replace("\\n", "\n").replace("'", "")


# item_type: 1 => 적합한 정치인 TOP, 2 => 적합한 정치인 WORST
# id => 정치인 id
# 랭킹 아이템을 갖다 댈시 그에 맞는 이유 표시
def on_report_item_hover(item_type: int, id: str):

    politician=get_object_or_404(Politician,str_id=id)

    politician_rank=(
        PoliticianReport.objects
        .filter(politician_id=politician)
        .order_by('-created_at')
        .first()
    )
    
    if not politician_rank:
        raise Http404("None rank")

    for i in range(0, 10):
        politician_rank.politicians_top[i]['reason'] = politician_rank.politicians_top[i]['reason'].replace("**", "").replace("\\n", "\n").replace("'", "")
        politician_rank.politicians_bottom[i]['reason'] = politician_rank.politicians_bottom[i]['reason'].replace("**", "").replace("\\n", "\n").replace("'", "")

    if item_type==1:
        return politician_rank.politicians_top
    else:
        return politician_rank.politicians_bottom

def IndividualPoliticians(request, str_id):
    politician=get_object_or_404(Politician,str_id=str_id)
    #str_id와 같은 아이디, Politician에서 갖고오기
    report=load_politician_report(str_id)
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
        'committees':politician.committees or '위원회 없음',
        'address':politician.address,
        'email':politician.email or '이메일 없음',
        'tel':politician.tel or '전화번호 없음',
        'profile':politician.profile.replace("\\n", "\n").replace("&middot;", "·"),
        'pic':politician.pic_link,
        'book':politician.books or '저서 없음',
        'curr_assets':politician.curr_assets,
        'boja':politician.boja,
        'top_secretary':politician.top_secretary,
        'secretary':politician.secretary,
        'bill_approved':politician.bill_approved,
        'election_name':politician.election_name,
        'election_type':politician.election_type,
        'politician_report':report,
        'best_rank':best_rank,
        "worst_rank":wort_rank,
        "str_id":politician.str_id,
    }

    return render(request,'main/politician_report.html',context)
  #endregion




#region 6 채팅 페이지
def GoToChat(request,str_id:str):
    #챗봇 상대의 해당하는 정치인 id를 받아, 해당 정치인의 성향 등을 반영한 정보를 기반으로 랜더링

    politicians = Politician.objects.filter(str_id=str_id)
    user_text = "" # 유저의 메시지는 어디서 가져올 것인가
    text = "" # 답변

    if request.method == "POST":
        message = request.POST.get('message')
        user_text = message

    if politicians:
        politician = politicians.first()

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
            '위원회':politician.committees or '위원회 없음',
            '주소':politician.address,
            '이메일':politician.email or '이메일 없음',
            '전화번호':politician.tel or '전화번호 없음',
            '경력':politician.profile,
            '저서':politician.books or '저서 없음',
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
        context = {
            "str_id": str_id,
            "name": politician.name,
            "pic_link": politician.pic_link,
            "response": f"안녕하십니까, {politician.name}입니다."
        }

        if user_text == "": # 첫 페이지
            if politician.name == "이재명":
                context["response"] = "안녕하십니까, 이제부터 진짜 대한민국! 지금은 이재명입니다."
            else:
                context["response"] = ManageChat(request, "(인삿말)", politician, poly_infos)[0]
            return render(request, "main/chat.html", context)

        response = ManageChat(request, user_text, politician, poly_infos)
        text = response[0]

        if text != "":
            user = User.objects.filter(id=get_user_id(request)).first()
            Chat.objects.create(user=user, text=user_text, role="user", token_count=response[1], politician_id=politician.str_id)
            Chat.objects.create(user=user, text=text, role="model", token_count=response[1], politician_id=politician.str_id)
    else:
        text = "잘못된 접근입니다. 올바른 정치인을 선택 후 다시 시도해주세요."

    if text == "":
        text = "죄송합니다. 하루 토큰 사용량을 초과하였습니다. 내일 다시 시도해주세요."

    context["response"] = text
    return render(request, "main/chat.html", context)

def ManageChat(request, user_text: str, politician: Politician, poly_infos: dict) -> tuple[str, int]:
    #사용자의 메세지를 받아,정치인 스타일로 AI 응답 반환
    #응답 생성은 CreateResponse()호출로 이루어짐
    
    prompt = []
    system = ""
    TONE_COUNT = 5
    TOKEN_LIMIT = 50 * 10000 #AVAILABLE RESPONSE COUNT * TOKEN USED PER RESPONSE

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

    speeches3 = Tone.objects.filter(name=politician.name)

    if speeches3:
        speeches2.append(speeches3.first().speech)

    user = User.objects.filter(id=get_user_id(request)).first()
    history = Chat.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-created_at')[:30]
    total_tokens = 0

    for chat in history:
        if chat.role == "user":
            continue
        total_tokens += chat.token_count
        
    if total_tokens >= TOKEN_LIMIT:
        return ("", 0)
    
    history2 = Chat.objects.filter(
        user=user,
        politician_id=politician.str_id,
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-created_at')[:30]
    
    for i in reversed(range(0, len(history2))):
        chat = history2[i]

        prompt.append({
            "role": chat.role,
            "parts": [
                {
                    "text": chat.text
                }
            ]
        })

    prompt.append({
            "role": "user",
            "parts": [
                {
                    "text": user_text
                }
            ]
        })

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
    
    if politician.name == "이재명":
        system += "\n참고로, 이재명은 제 21대 대선에 1위되어서 2025년 6월 3일부터 대한민국 대통령이 되었어. 그 점 참고하고 이야기해줘. 또한, 그 나머지 후보인 김문수, 이준석, 권영국 후보는 당선되지 못했어."

    ai_text = CreateResponse(prompt, system) # 로직 구현 필요
    # 문제점: 텍스트만 생성해야 하고, 딴 질문에는 답변하지 않아야 함. 그런 제한할 수 있는 기능이 있나?

    return ai_text

def CreateResponse(prompt: str | list, system = "")-> tuple[str, int]: # (text, token_count)
    #정치인 말투에 맞게 응답을 만들어내는 AI 호출
    config = None

    if system != "":
        config = types.GenerateContentConfig(system_instruction=system)

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash-preview-05-20",
        contents=prompt,
        config=config
    )
    
    return (response.text.replace("**", "").replace("\\n", "\n").replace("'", ""), response.usage_metadata.total_token_count)
#endreigon




#region 7 분야별 랭킹 페이지
def PoliticianRanking(request):

    sort_by=request.GET.get('sort','reelected')
    order=request.GET.get('order')

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
        ),
        curr_assets_int=Cast('curr_assets', IntegerField())
    )

    #정렬 기준 설정(정렬 필드)
    sort_fields={
        'reelected':'reelected_count',
        'curr_assets':'curr_assets_int',
        'birthdate':'age',
        'attendance':'attendance_plenary',
        'election_gap':'election_gap',
    }


    #기본 정렬 기준 설정(다선여부)
    standard_order_field=sort_fields.get(sort_by,'reelected_count')

    #null값 필드 지정정
    null_fields=['attendance','election_gap']


    #방향 기본값
    is_asc=order=='asc'

    # 정렬 로직 적용
    if sort_by in null_fields:
        field = F(standard_order_field).asc(nulls_last=True) if is_asc else F(standard_order_field).desc(nulls_last=True)
        politicians = politicians.order_by(field)
    else:
        prefix = '' if is_asc else '-'
        politicians = politicians.order_by(prefix + standard_order_field)        
    #페이지네이션
    paginator=Paginator(politicians,20)
    page_num=request.GET.get('page')
    page_obj=paginator.get_page(page_num)

    #넘겨줄 정보 만들기
    context={
        'politicians':page_obj,
        'sort_by':sort_by,
        'order':'asc' if is_asc else 'desc',
    }

    return render(request,'main/politician_ranking.html',context)
#endregion



#region 8 지난 리포트 다시보기 페이지
# def get_user_id(request):
#     if not request.session.session_key:
#         request.session.create()
    
#     # 2. Django 세션에서 User UUID 가져오기 (사용자 식별용)
#     user_uuid = request.session.get('user_uuid')
#     return user_uuid

# 이 함수 uuid없으면 2페이지 보내야 하는 거 아님?
# def ReportHistory(request):
#     #쿠키에서 리포트 목록을 가져와 템플릿에 랜더링
#     id = get_user_id(request)
#     responses = UserReport.objects.filter(user_id=id)
#     responses2: dict[list[UserReport]] = {}

#     for response in responses:
#         if responses2[response.created_at] is None:
#             responses2[response.created_at] = []
#         responses2[response.created_at].append(response)

#     context = {
#         "reports": []
#     }
#     i = 0

#     for reports in responses2:
#         if i >= 10: # limit
#             break

#         for report in reports:
#             if i >= 10: # limit
#                 break

#             ratio = int(round(report.user_overall_tendency, 0))

#             context["reports"].append({
#                 "rank": i + 1,
#                 "date": report.created_at,
#                 "party": report.parties_rank[0]["name"],
#                 "politician": report.politicians_top[0]["name"],
#                 "ratio": ratio,
#                 "ratio2": 100 - ratio
#             })
#             i += 1
    
#     return render(request, 'main/history.html', context)
# #endregion

def ReportHistory(request):
    try:
        user_uuid = get_user_id(request)
        
        if not user_uuid:
            return redirect('question_page', page_num=1)
        
        try:
            current_user = User.objects.get(id=user_uuid)
        except User.DoesNotExist:
            return redirect('question_page', page_num=1)
        
        # 사용자의 모든 완료된 리포트 조회 (최신순)
        user_reports = UserReport.objects.filter(
            user=current_user
        ).order_by('-created_at')
        
        if not user_reports.exists():
            return redirect('question_page', page_num=1)
        
        # history.html 템플릿에 맞는 데이터 구조로 변환
        reports = []
        for i, report in enumerate(user_reports[:10]):  # 최신 10개만
            # 정당 랭킹에서 1위 정당 가져오기
            top_party = "정당 없음"
            if report.parties_rank and len(report.parties_rank) > 0:
                top_party = report.parties_rank[0].get('name', '정당 없음')
            
            # 정치인 TOP에서 1위 정치인 가져오기
            top_politician = "정치인 없음"
            if report.politicians_top and len(report.politicians_top) > 0:
                top_politician = report.politicians_top[0].get('name', '정치인 없음')
            
            # 성향 비율 계산 (0~1을 0~100으로 변환)
            ratio = int(round(report.user_overall_tendency * 100, 0))
            ratio2 = 100 - ratio
            
            reports.append({
                "rank": i + 1,
                "created_at": report.created_at,
                "party": top_party,
                "politician": top_politician,
                "ratio": ratio,
                "ratio2": ratio2
            })
        
        context = {
            "reports": reports  # 템플릿에서 기대하는 'reports' 키로 전달
        }
        
        return render(request, 'main/history.html', context)
        
    except Exception as e:
        print(f"ReportHistory 오류: {e}")
        return redirect('question_page', page_num=1)
