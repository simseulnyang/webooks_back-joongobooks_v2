import factory
from factory.django import DjangoModelFactory, ImageField
from books.models import Book, Favorite
from accounts.factories import UserFactory


class BookFactory(DjangoModelFactory):
    class Meta:
        model = Book
    
    writer = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f'테스트 책 {n}')
    author = factory.Faker('name', locale='ko_KR')
    publisher = factory.Faker('company', locale='ko_KR')
    condition = '최상'
    original_price = factory.Faker('random_int', min=5000, max=50000)
    selling_price = factory.Faker('random_int', min=1000, max=30000)
    detail_info = factory.Faker('text', locale='ko_KR', max_nb_chars=200)
    category = Book.Category.NOVEL
    sale_condition = Book.SALE_CONDITION_CHOICES.FOR_SALE
    
    # 가짜 이미지 필드 생성
    book_image = ImageField(filename='test_book.jpg')
    
    
class FavoriteFactory(DjangoModelFactory):
    class Meta:
        model = Favorite
        
    user = factory.SubFactory(UserFactory)
    book = factory.SubFactory(BookFactory)