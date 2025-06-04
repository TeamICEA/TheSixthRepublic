from django.urls import path
from . import views

urlpatterns = [
    #path('', views.index, name='index'),

    # 2 질문지 페이지
    path('questions/<int:page_num>/', views.question_page, name='question_page'),
    path('result/', views.result_page, name='result_page'),

    # 3 리포트 페이지


    # 4 정치인 목록 페이지
    path('politicians/', views.politician_list, name='politician_list'),
    path('politicians/<int:politician_id>/', views.politician_detail, name='politician_detail'),



    # 몇 페이지인지 주석 써주세요.
    path('', views.index, name='index'),

    #개별 정치인 분석 페이지지
    path('<str:str_id>/',views.IndividualPoliticians,name='IndividualPoliticians'),
    
    #랭킹 페이지지
    path('ranking/',views.PoliticianRanking,name='PoliticianRanking'),
]