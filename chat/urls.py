from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    # 채팅방
    path("rooms/", views.ChatRoomListView.as_view(), name="room-list"),
    path("rooms/create/", views.ChatRoomCreateOrGetView.as_view(), name="room-create"),
    path("rooms/<int:chatroom_id>/", views.ChatRoomDetailView.as_view(), name="room-detail"),
    # 메시지
    path("rooms/<int:chatroom_id>/messages/", views.MessageListView.as_view(), name="message-list"),
    # 안 읽은 메시지 개수
    path("unread-count/", views.UnreadCountView.as_view(), name="unread-count"),
]
