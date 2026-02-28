from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import StudentSignupSerializer
from .models import User, StudentProfile, AcademicRecord


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


@api_view(['GET'])
def get_user_info(request):
    """
    Open GET endpoint — no authentication required.
    Returns full info for a student by username.

    GET /accounts/api/user-info/?username=<username>
    """
    username = request.query_params.get('username', '').strip()
    if not username:
        return Response(
            {"success": False, "error": "'username' query parameter is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {"success": False, "error": f"No user found with username '{username}'."},
            status=status.HTTP_404_NOT_FOUND
        )

    # --- Base user data ---
    data = {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_student": user.is_student,
            "is_moderator": user.is_moderator,
            "is_organization": user.is_organization,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
        },
        "student_profile": None,
        "academic_records": [],
    }

    # --- Student profile ---
    try:
        profile = user.studentprofile
        data["student_profile"] = {
            "full_name": profile.full_name,
            "dob": profile.dob,
            "gender": profile.gender,
            "father_name": profile.father_name,
            "mother_name": profile.mother_name,
            "annual_income": str(profile.annual_income) if profile.annual_income is not None else None,
            "caste_category": profile.caste_category,
            "is_disabled": profile.is_disabled,
            "phone": profile.phone,
            "address": profile.address,
            "pin_code": profile.pin_code,
            "city": profile.city,
            "state": profile.state,
            "aadhaar_number": profile.aadhaar_number,
            "bank_account_number": profile.bank_account_number,
            "bank_ifsc_code": profile.bank_ifsc_code,
            "bank_name": profile.bank_name,
            "otr_completed": profile.otr_completed,
            "otr_step": profile.otr_step,
            "profile_completion": profile.profile_completion,
            "total_karma_points": profile.total_karma_points,
            "karma_rank": profile.karma_rank,
            "verified_scholar_badge": profile.verified_scholar_badge,
            "created_at": profile.created_at,
        }

        # --- Academic records ---
        records = AcademicRecord.objects.filter(student=profile)
        data["academic_records"] = [
            {
                "id": r.id,
                "degree_level": r.degree_level,
                "stream": r.stream,
                "institution_name": r.institution_name,
                "current_year": r.current_year,
                "last_exam_score": str(r.last_exam_score) if r.last_exam_score is not None else None,
            }
            for r in records
        ]
    except StudentProfile.DoesNotExist:
        pass  # user exists but has no student profile yet

    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_user_documents(request):
    """
    Open GET endpoint — no authentication required.
    Returns all uploaded documents for a student by username.

    GET /accounts/api/user-documents/?username=<username>

    Response includes document type name, full file URL,
    verification status, upload time, and any notes.
    """
    username = request.query_params.get('username', '').strip()
    if not username:
        return Response(
            {"success": False, "error": "'username' query parameter is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response(
            {"success": False, "error": f"No user found with username '{username}'."},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        profile = user.studentprofile
    except StudentProfile.DoesNotExist:
        return Response(
            {
                "success": True,
                "username": username,
                "document_count": 0,
                "documents": [],
                "message": "User exists but has no student profile yet.",
            },
            status=status.HTTP_200_OK
        )

    documents = profile.documents.all().order_by('document_type')

    doc_list = []
    for doc in documents:
        # Build an absolute URL so the caller can directly download the file
        try:
            file_url = request.build_absolute_uri(doc.file.url) if doc.file else None
        except Exception:
            file_url = None

        doc_list.append({
            "id": doc.id,
            "document_type": doc.document_type,
            "document_type_label": doc.get_document_type_display(),
            "file_url": file_url,
            "uploaded_at": doc.uploaded_at,
            "is_verified": doc.is_verified,
            "verification_status": doc.verification_status,
            "notes": doc.notes,
        })

    return Response(
        {
            "success": True,
            "username": username,
            "full_name": profile.full_name,
            "document_count": len(doc_list),
            "documents": doc_list,
        },
        status=status.HTTP_200_OK
    )
