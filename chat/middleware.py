import logging

from django.contrib.auth.models import AnonymousUser

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()

        headers = dict(scope.get("headers", []))
        raw = headers.get(b"sec-websocket-protocol")

        if not raw:
            logger.warning("[JWT MW] no sec-websocket-protocol header")
            return await super().__call__(scope, receive, send)

        try:
            proto = raw.decode("utf-8")
            parts = [p.strip() for p in proto.split(",")]
            logger.warning(f"[JWT MW] sec-websocket-protocol parts={parts}")

            token = None

            # 케이스 1) ["Authorization", "Bearer <token>"]
            if len(parts) >= 2 and parts[0].lower() == "authorization":
                token_part = parts[1]
                if token_part.lower().startswith("bearer "):
                    token = token_part.split(" ", 1)[1].strip()
                else:
                    # 혹시 "Bearer"와 토큰이 분리된 경우 대비
                    token = token_part.strip()

            # 케이스 2) ["Bearer <token>"] 같은 단일 값으로 오는 경우도 방어
            if token is None and len(parts) == 1:
                if parts[0].lower().startswith("bearer "):
                    token = parts[0].split(" ", 1)[1].strip()

            if not token:
                logger.warning("[JWT MW] token not found in sec-websocket-protocol")
                return await super().__call__(scope, receive, send)

            user = await self.get_user(token)
            scope["user"] = user
            logger.warning(f"[JWT MW] authenticated user={user}")

        except Exception as e:
            logger.exception(f"[JWT MW] failed to authenticate: {e}")

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, token: str):
        jwt_auth = JWTAuthentication()
        validated = jwt_auth.get_validated_token(token)
        return jwt_auth.get_user(validated)
