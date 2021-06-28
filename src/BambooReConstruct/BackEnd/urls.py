from django.urls import path

from BackEnd.views import *

urlpatterns = [
    path("example/" , example , name="example") ,
    path('upload/' , upload , name="file_upload") ,
    path("graph/<str:uid>" , graph) ,
    path("export/<str:uid>" , export_result),
    path("recover/<str:uid>",recover),
    path("add_param/<str:uid>/" , add_param) ,

]
