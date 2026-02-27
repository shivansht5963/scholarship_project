from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import StudentSignupSerializer
from .models import User, StudentProfile


@api_view(['POST'])
def student_signup(request):
    """
    Open POST endpoint for the external student-verification project.
    Receives verified student data and creates a User + StudentProfile.

    POST /accounts/api/student-signup/
    """
    serializer = StudentSignupSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = serializer.validated_data

    try:
        with transaction.atomic():
            # 1. Create the Django User
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                is_student=True,
                is_moderator=False,
                is_organization=False,
            )

            # 2. Create the linked StudentProfile
            StudentProfile.objects.create(
                user=user,
                full_name=data['full_name'],
                phone=data.get('phone', ''),
                gender=data.get('gender', ''),
                dob=data.get('dob', None),
                father_name=data.get('father_name', ''),
                mother_name=data.get('mother_name', ''),
                annual_income=data.get('annual_income', None),
                caste_category=data.get('caste_category', ''),
                is_disabled=data.get('is_disabled', False),
                address=data.get('address', ''),
                city=data.get('city', ''),
                state=data.get('state', ''),
                pin_code=data.get('pin_code', ''),
                aadhaar_number=data.get('aadhaar_number', None),
                bank_account_number=data.get('bank_account_number', ''),
                bank_ifsc_code=data.get('bank_ifsc_code', ''),
                bank_name=data.get('bank_name', ''),
                otr_completed=False,
                otr_step=1,
            )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response(
        {
            "success": True,
            "message": f"Student '{user.username}' registered successfully.",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        },
        status=status.HTTP_201_CREATED
    )
