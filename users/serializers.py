from rest_framework import serializers
from .models import User, StudentProfile


class StudentSignupSerializer(serializers.Serializer):
    # --- Required Fields ---
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    full_name = serializers.CharField(max_length=150)

    # --- Optional Profile Fields ---
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    gender = serializers.ChoiceField(
        choices=['Male', 'Female', 'Other'],
        required=False,
        allow_blank=True,
        default=''
    )
    dob = serializers.DateField(required=False, allow_null=True)
    father_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    mother_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    annual_income = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    caste_category = serializers.ChoiceField(
        choices=['General', 'OBC', 'SC', 'ST', 'EWS'],
        required=False,
        allow_blank=True,
        default=''
    )
    is_disabled = serializers.BooleanField(required=False, default=False)
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    pin_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    aadhaar_number = serializers.CharField(max_length=12, required=False, allow_blank=True)
    bank_account_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    bank_ifsc_code = serializers.CharField(max_length=11, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_aadhaar_number(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Aadhaar number must contain only digits.")
        if value and len(value) != 12:
            raise serializers.ValidationError("Aadhaar number must be exactly 12 digits.")
        return value or None
