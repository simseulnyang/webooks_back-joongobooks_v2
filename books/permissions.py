from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    객체의 소유자만 수정/삭제 가능
    
    - 읽기 권한: 모든 인증된 사용자
    - 쓰기 권한: 객체 소유자만
    """
    
    def has_object_permission(self, request, view, obj):
        # 읽기 권한은 모두에게
        if request.method in SAFE_METHODS:
            return True
        
        # 쓰기 권한은 소유자만
        return obj.writer == request.user


class IsOwner(BasePermission):
    """
    객체의 소유자만 모든 작업 가능
    """
    
    def has_object_permission(self, request, view, obj):
        return obj.writer == request.user