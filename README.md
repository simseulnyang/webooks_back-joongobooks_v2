# 📚 WeBooks Backend API

> **중고책 거래 플랫폼 – 실전 환경을 고려한 소셜 인증, 실시간 채팅, CI/CD 기반 백엔드 프로젝트**

[![Django](https://img.shields.io/badge/Django-5.1.4-092E20?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15.2-ff1709)](https://www.django-rest-framework.org/)
[![Poetry](https://img.shields.io/badge/Poetry-Dependency%20Management-60A5FA)](https://python-poetry.org/)
[![Tests](https://img.shields.io/badge/Tests-Passing-success)](https://github.com/yourusername/webooks-backend)

---

## 📌 프로젝트 배경

중고책 거래 서비스는 **개인 간 거래**, **인증**, **권한 제어**, **실시간 커뮤니케이션**이 동시에 요구되는 도메인입니다.  
본 프로젝트는 단순 CRUD 구현을 넘어, **실제 서비스 환경에서 발생할 수 있는 인증·보안·운영 이슈를 직접 설계하고 해결해보는 것**을 목표로 시작했습니다.

특히 다음과 같은 질문에서 출발했습니다.

- 소셜 로그인은 어디까지 서버에서 검증해야 안전한가?
- Provider별 OAuth 정책 차이를 어떻게 관리해야 유지보수가 쉬운가?
- 인증이 포함된 API를 어떻게 테스트해야 신뢰할 수 있는가?

이 프로젝트는 위 질문들에 대한 **구조적 해답을 코드로 구현한 백엔드 포트폴리오**입니다.

---

## 🎯 핵심 구현 사항

### 1️⃣ 소셜 인증 시스템 (Kakao / Google)

- **Kakao / Google OAuth 2.0 분리 구현**
  - Provider별 정책 차이를 고려한 독립 엔드포인트 설계
  - 공통화로 인한 복잡도 증가 대신, 명확한 책임 분리 선택

- **JWT 기반 인증 구조**
  - SimpleJWT 기반 Access / Refresh Token 발급
  - Refresh Token Blacklist 적용으로 로그아웃·탈취 대응

- **서버 측 Google ID Token 검증**
  - 클라이언트 위·변조 가능성 차단
  - OAuth Best Practice에 따른 보안 강화

```python
from google.oauth2 import id_token
from google.auth.transport import requests

idinfo = id_token.verify_oauth2_token(
    token, requests.Request(), settings.GOOGLE_CLIENT_ID
)
```

## 2️⃣ 실전 상황을 고려한 예외 처리 전략

### Provider별 인증 실패 시나리오 분기 처리
- 이메일 미제공
- 토큰 만료
- 잘못된 provider 요청

### HTTP 상태 코드 명확화
- `400 Bad Request`
- `409 Conflict`

### 에러 응답 설계
- 사용자 친화적 메시지 제공
- `errors` 필드를 통한 상세 원인 전달

> “에러가 나지 않는 코드”가 아니라  
> **“에러가 나도 설명 가능한 코드”**를 목표로 설계

---

## 3️⃣ CI/CD 기반 개발 워크플로우 구축

### GitHub Actions 자동화 파이프라인
- Black / isort / Flake8을 통한 코드 품질 검사
- pytest 기반 테스트 자동 실행
- Poetry 캐싱을 통한 빌드 시간 단축

### 테스트 전략
- Factory Boy를 활용한 테스트 데이터 독립성 확보
- 모델 / 시리얼라이저 / 뷰 계층별 분리 테스트
- 인증·권한 시나리오 통합 테스트

```python
class BookFactory(DjangoModelFactory):
    class Meta:
        model = Book

    writer = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"테스트 책 {n}")
    original_price = factory.Faker("random_int", min=5000, max=50000)
```

## 4️⃣ REST API 설계 Best Practice 적용
- drf-spectacular 기반 OpenAPI 3.0 자동 문서화
- 명확한 리소스 분리
    - /accounts/
    - /api/books/
    - /api/chat/
- Pagination / Filtering / Ordering 지원
- 커스텀 Permission (IsOwnerOrReadOnly) 구현

---

## 🤔 기술적 의사결정 포인트

### 왜 OAuth Provider를 분리했는가?
- Provider별 응답 구조와 정책이 상이
- 변경 시 영향 범위 최소화
- 디버깅 및 테스트 단순화

### 왜 서버에서 ID Token을 검증했는가?
- 클라이언트 토큰 위·변조 방지
- 중간자 공격 대응
- OAuth 공식 권장 방식 준수

---

## 🔐 보안 고려사항

| 항목 | 구현 내용 |
|------|----------|
| 토큰 관리 | Access Token (15분) + Refresh Token (7일), 로그아웃 시 Blacklist 처리 |
| OAuth 검증 | Google ID Token 서버 검증, Kakao 사용자 정보 API 직접 호출 |
| 환경 변수 | `.env` 파일로 민감 정보 분리 및 Git 제외 |
| CORS | 프로덕션 환경에서 허용 도메인 제한 |
| Permission | IsAuthenticated, IsOwner 등 계층별 권한 제어 |

---

## 📈 성능 및 확장 고려

- `select_related` / `prefetch_related`로 N+1 쿼리 방지
- Pagination 기본 적용 (10개 단위)
- Redis 기반 캐싱 구조 설계 경험
  - 실제 서비스 확장을 고려한 구조 설계 (향후 적용 예정)

---

## 🛠 기술 스택

| Category | Technologies |
|----------|-------------|
| **Framework** | Django 5.1.4, Django REST Framework 3.15.2 |
| **Auth** | SimpleJWT, OAuth 2.0 |
| **DB** | PostgreSQL |
| **Real-time** | Django Channels, Channels-Redis (WebSocket) |
| **Docs** | drf-spectacular (OpenAPI 3.0) |
| **Test** | pytest-django, Factory Boy |
| **Code Quality** | Black, isort, Flake8 |
| **CI** | GitHub Actions |
| **Dependency** | Poetry |

---

## 📊 아키텍처 설계
```
webooks-backend/
├── config/                    # 프로젝트 설정
├── accounts/                  # 사용자 인증 (OAuth, JWT)
│   ├── views.py              # KakaoLoginAPIView, GoogleLoginAPIView
│   ├── serializers.py        # 소셜 로그인 응답 직렬화
│   └── tests/                # 인증 시나리오 테스트
├── books/                     # 책 CRUD 및 좋아요
│   ├── models.py             # Book, Favorite 모델
│   ├── permissions.py        # IsOwnerOrReadOnly 등
│   ├── pagination.py         # 커스텀 페이지네이션
│   └── tests/                # 모델/뷰/직렬화 테스트
├── chat/                      # 실시간 채팅
│   ├── consumers.py          # WebSocket Consumer
│   └── routing.py            # WebSocket URL 라우팅
└── pyproject.toml            # Poetry 의존성 정의
```

---

## 🚀 실행 방법

### 환경 설정

```bash
# 1. Poetry 설치
curl -sSL https://install.python-poetry.org | python3 -

# 2. 의존성 설치
poetry install

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에 다음 설정 필수:
# - SECRET_KEY
# - KAKAO_REST_API_KEY
# - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
# - DB 설정 (PostgreSQL)

# 4. 마이그레이션 및 실행
poetry run python manage.py migrate
poetry run python manage.py runserver
```

---

## 🙋‍♂️ 담당 역할 및 성장 포인트
- 백엔드 전체 설계 및 구현
- OAuth 인증 구조 설계
- JWT 보안 정책 수립
- 테스트 및 CI/CD 환경 구축
이 프로젝트를 통해
**"기능 구현"보다 "운영과 유지보수를 고려한 설계"**의 중요성을 체감했습니다.

---

## 🌱 이 프로젝트를 통해 얻은 것

- OAuth 2.0 실전 적용 경험
- REST API 설계 역량
- 테스트 기반 개발 경험
- CI/CD 자동화에 대한 이해