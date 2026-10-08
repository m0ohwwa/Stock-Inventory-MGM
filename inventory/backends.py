from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom Authentication Backend allowing users to log in with either
    their Email address or Username.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Try finding user by email only (case-insensitive)
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            # Prevent timing attack
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email__iexact=username).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
