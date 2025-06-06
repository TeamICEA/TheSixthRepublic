from django.urls import path
from . import views

urlpatterns = [
    #path('', views.index, name='index'),

    # 스마트 설문 리다이렉트 (베너용)
    path('survey/', views.smart_survey_redirect, name='smart_survey_redirect'),

    # 2 질문지 페이지
    path('questions/<int:page_num>/', views.question_page, name='question_page'),
    path('result/', views.result_page, name='result_page'),

    # 3 리포트 페이지(석환)
    path('userreport',views.ShowUserReport,name='user_report'),

    # 4 정치인 목록 페이지
    path('politicians/', views.politician_list, name='politician_list'),
    
    # 얜 뭐지?
    path('politicians/<int:politician_id>/', views.politician_detail, name='politician_detail'),

    # 7 랭킹 페이지
    path('ranking/',views.PoliticianRanking,name='politician_ranking'),

    # 6 채팅 페이지
    path('chat/<str:str_id>', views.GoToChat, name='chat'),


    # 8 리포트 다시보기 페이지
    path('history/', views.ReportHistory, name='history'),


    # 5 개별 정치인 분석 페이지
    path('<str:str_id>/',views.IndividualPoliticians,name='politician_report'),


    # 몇 페이지인지 주석 써주세요.
    path('', views.index, name='index'),
]