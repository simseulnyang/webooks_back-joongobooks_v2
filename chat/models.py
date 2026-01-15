from django.contrib.auth import get_user_model
from django.db import models

from books.models import Book

User = get_user_model()


class ChatRoom(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chat_rooms", verbose_name="관련 책")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buyer_chatrooms", verbose_name="구매자")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_chatrooms", verbose_name="판매자")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("book", "buyer")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.book.title} | 구매자 : {self.buyer.username} & 판매자 : {self.seller.username}"

    @property
    def room_group_name(self):
        return f"chat_{self.id}"

    def is_participant(self, user):
        """사용자가 이 채팅방의 참여자인지 확인"""
        return user == self.buyer or user == self.seller

    def get_other_user(self, user):
        """상대방 유저 반환"""
        if user == self.buyer:
            return self.seller
        return self.buyer


class Message(models.Model):
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages", verbose_name="채팅방")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_message", verbose_name="발신자")
    content = models.TextField(verbose_name="메시지 내용")
    is_read = models.BooleanField(default=False, verbose_name="읽음 여부")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:30]}"
