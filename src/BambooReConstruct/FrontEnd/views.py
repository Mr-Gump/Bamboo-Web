import sys

from django.shortcuts import render

sys.path.append("..")
from Tools import Tools


def welcome(request):
    return render(request , "welcome.html")


def upload(request):
    files = [[index + 1 , i['uid'] , i['point_num'] , i['time_points'][0] , i['time_points'][-1]] for index , i in
             enumerate(Tools.scan_history_file())]
    return render(request , "upload.html" , locals())


def caculate(request , uid):
    return render(request , "calculate.html" , locals())


def result(request , uid):
    point_num = eval(request.GET.get("point_num"))
    points = [i + 1 for i in range(point_num)]
    return render(request , "result.html" , locals())


def addParam(request , uid):
    return render(request , "addParam.html" , locals())
