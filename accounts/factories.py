import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from accounts.models import SocialAccount

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'testuser{n}@example.com')
    username = factory.Sequence(lambda n: f'테스트유저{n}')
    profile_image = factory.Faker('image_url')
    
    is_staff = False
    is_superuser = False
    is_active = True
    
    
class SocialAccountFactory(DjangoModelFactory):
    class Meta:
        model = SocialAccount

    user = factory.SubFactory(UserFactory)
    provider = SocialAccount.Provider.GOOGLE
    provider_user_oid = factory.Sequence(lambda n: f'google_oid_{n}')