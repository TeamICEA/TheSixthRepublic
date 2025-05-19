from django.urls import path
from . import views

urlpatterns = [
    #path('', views.index, name='index'),

    # 2 질문지 페이지
    path('questions/<int:page_num>/', views.question_page, name='question_page'),
    path('result/', views.result_page, name='result_page'),

    # 3 리포트 페이지


    # 4 정치인 목록 페이지
    path('politicians/', views.FilteredInquiry, name='politician_list'),
    path('politicians/<int:int_id>/', views.GoToPoliticianPage, name='politician_detail'),


]