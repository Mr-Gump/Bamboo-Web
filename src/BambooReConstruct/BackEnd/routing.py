from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    url(r'^ws/data_stream/(?P<uid>[^/]+)/$', consumers.MyConsumer.as_asgi()),
]
