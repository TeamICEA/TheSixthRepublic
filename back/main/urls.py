from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
]

# 2 설문지 페이지
urlpatterns = [
    path('questions/<int:page_num>/', views.question_page, name='question_page'),
    path('result/', views.result_page, name='result_page'),
]