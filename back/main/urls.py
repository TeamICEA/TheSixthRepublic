from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('<str:str_id>/',views.IndividualPoliticians,name='IndividualPoliticians'),
    path('ranking/',views.politician_ranking,name='politician_ranking'),
]