from django.urls import path

from FrontEnd.views import *

urlpatterns = [
    path('' , welcome) ,
    path("welcome/" , welcome) ,
    path("upload/" , upload , name="upload") ,
    path("calculate/<str:uid>" , caculate , name="caculate") ,
    path("result/<str:uid>" , result) ,
    path("add-param/<str:uid>" , addParam)
]
