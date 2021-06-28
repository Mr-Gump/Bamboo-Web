import json
import sys
import time
from multiprocessing import Process

from channels.generic.websocket import WebsocketConsumer

sys.path.append("..")
from Work import Work


class MyConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()
        self.uid = self.scope['url_route']['kwargs']['uid']
        self.work = Work(self.uid)

    def receive(self , text_data=None , bytes_data=None):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        received_uid = text_data_json["uid"]
        print(message , received_uid)
        if message == 'ready' and received_uid == self.uid:
            point_num = self.work.info["NXP"]
            self.send(text_data=json.dumps({
                'message': "point_num" ,
                'data': point_num ,
                'uid': self.uid
            }))
        elif message == 'start' and received_uid == self.uid:
            main_work_process = Process(target=self.work.main_work)
            main_work_process.start()
            self.message_consumer()
            main_work_process.join()
            self.send(text_data=json.dumps({
                'message': "finished" ,
                'data': None ,
                'uid': self.uid
            }))
        else:
            self.send(text_data=json.dumps({
                'message': "invalid message" ,
                'data': None ,
                'uid': self.uid
            }))

    def disconnect(self , code):
        print(f"已断开websocket({self.uid})连接")

    def message_consumer(self):
        while True:
            time.sleep(0.5)
            if not self.work.q.empty():
                data = self.work.q.get()
                if data == -1:
                    return

                self.send(text_data=json.dumps({
                    'message': "caculating" ,
                    'data': data ,
                    'uid': self.uid
                }))

