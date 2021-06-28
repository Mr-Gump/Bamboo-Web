import json
import os
import sys

from django.http import StreamingHttpResponse , HttpResponse
from django.views.decorators.csrf import csrf_exempt

sys.path.append("..")
from Tools import Tools
from Work import Work


def example(request):
    file_name = os.path.join(Tools.static_dir , "example.xlsx")
    response = StreamingHttpResponse(Tools.file_iterator(file_name))
    response["Content-Type"] = "application/octet-stream"
    response["Content-Disposition"] = 'attachment; filename={0}'.format("example.xlsx")
    response["Access-Control-Expose-Headers"] = "Content-Disposition"

    return response


def upload(request):
    if request.method == 'POST':
        file = request.FILES["upload"]
        file_name = file.name
        file_chunks = file.chunks()
        work = Tools.handle_uploaded_file(file_name , file_chunks)
        status_code = work.status_code
        uid = work.uid
        msg = work.msg
    else:
        status_code = 501
        msg = "请求方式错误"
        uid = -1
    return HttpResponse(
        json.dumps({"status_code": status_code , "msg": msg , "uid": str(uid)}) ,
        content_type="application/json")


def graph(request , uid):
    point_num = eval(request.GET.get("point_num"))
    kind = eval(request.GET.get("kind"))
    html = Tools.gen_graph(uid , point_num , kind)
    return HttpResponse(html)


def export_result(request , uid):
    if request.method == 'GET':
        data = request.GET.get('data')
        img = request.GET.get('image')
        gif = request.GET.get("gif")
        if data == '1':
            data = True
        else:
            data = False
        if img == '1':
            img = True
        else:
            img = False
        if gif == '1':
            gif = True
        else:
            gif = False
        work = Work(uid)
        zip_path , file_name = work.export(data , img , gif)

        response = StreamingHttpResponse(Tools.file_iterator(zip_path))
        response["Content-Type"] = "application/octet-stream"
        response["Content-Disposition"] = 'attachment; filename={0}'.format(file_name)
        response["Access-Control-Expose-Headers"] = "Content-Disposition"

        return response


def recover(request , uid):
    step = request.GET.get('step')
    work = Work(uid)

    new_uid = work.recover_work(uid , int(step))
    return HttpResponse(
        json.dumps({"status_code": work.status_code , "message": work.msg , "uid": str(new_uid)}) ,
        content_type="application/json")


@csrf_exempt
def add_param(request , uid):
    data = request.body
    work = Work(uid)
    work.add_param(json.loads(data))
    return HttpResponse(
        json.dumps({"status_code": work.status_code , "message": work.msg , "uid": str(uid)}) ,
        content_type="application/json")
