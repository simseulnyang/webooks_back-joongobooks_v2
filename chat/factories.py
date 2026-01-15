import factory
from factory.django import DjangoModelFactory

from accounts.factories import UserFactory
from books.factories import BookFactory

from chat.models import ChatRoom, Message


class ChatRoomFactory(DjangoModelFactory):
    class Meta:
        model = ChatRoom
        
    book = factory.SubFactory(BookFactory)
    buyer = factory.SubFactory(UserFactory)
    seller = factory.SubFactory(UserFactory)


class MessageFactory(DjangoModelFactory):
    class Meta:
        model = Message

    chatroom = factory.SubFactory(ChatRoomFactory)
    sender = factory.SubFactory(UserFactory)
    content = factory.Faker('text', locale='ko-kr', max_nb_chars=100)
    is_read = False
