import random
import secrets
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings

class OTPGenerator:
    """
    Utility class for generating, storing, verifying, and sending OTP codes
    for Sign Up, Password Reset, and Authentication flows.
    """
    
    @staticmethod
    def generate_code(length=6):
        """Generates a secure numeric OTP code of specified length."""
        # Using secrets module for cryptographic randomness
        digits = [str(secrets.randbelow(10)) for _ in range(length)]
        return "".join(digits)

    @staticmethod
    def store_in_session(request, key_prefix, email, otp_code, extra_data=None):
        """Stores OTP code, timestamp, and optional extra data into session."""
        request.session[f'{key_prefix}_email'] = email
        request.session[f'{key_prefix}_otp'] = otp_code
        request.session[f'{key_prefix}_timestamp'] = timezone.now().timestamp()
        if extra_data:
            request.session[f'{key_prefix}_data'] = extra_data

    @staticmethod
    def verify_session_otp(request, key_prefix, input_otp, max_age_seconds=600):
        """Verifies entered OTP against stored session OTP within expiration limit."""
        stored_otp = request.session.get(f'{key_prefix}_otp')
        timestamp = request.session.get(f'{key_prefix}_timestamp', 0)
        now_ts = timezone.now().timestamp()

        if not stored_otp or not input_otp:
            return False, "No active OTP found. Please request a new code."

        if now_ts - timestamp > max_age_seconds:
            return False, "OTP code has expired. Please request a new code."

        if input_otp.strip() == str(stored_otp).strip():
            return True, "OTP verified successfully!"

        return False, "Invalid OTP code. Please check your code and try again."

    @staticmethod
    def clear_session_otp(request, key_prefix):
        """Clears OTP state from session upon successful verification."""
        for key in [f'{key_prefix}_email', f'{key_prefix}_otp', f'{key_prefix}_timestamp', f'{key_prefix}_data']:
            request.session.pop(key, None)

    @staticmethod
    def send_email(email, otp_code, purpose='signup', username=None):
        """Sends OTP code via Django send_mail."""
        display_name = username or email
        if purpose == 'forgot_password':
            subject = "Password Reset OTP Code - Stock Inventory System"
            message = (
                f"Hello {display_name},\n\n"
                f"We received a request to reset your password for Stock Inventory System.\n"
                f"Your verification code is:\n\n  {otp_code}\n\n"
                f"If you did not request a password reset, please ignore this email.\n"
                f"This code will expire in 10 minutes."
            )
        else:
            subject = "Your Stock Inventory verification code"
            message = (
                f"Hi {display_name},\n\n"
                f"Your verification code is:\n\n  {otp_code}\n\n"
                f"Expires in 10 minutes.\n\n"
                f"— Stock Inventory Team"
            )

        return send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
