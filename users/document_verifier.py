"""
users/document_verifier.py
--------------------------
Gemini Vision API integration for verifying student documents uploaded in OTR Step 5.
Each document type has a tailored prompt. Results are stored as JSON on the StudentDocument.
"""

import json
import re
import google.generativeai as genai
from django.conf import settings
from PIL import Image
import io


# ─── Configure Gemini ──────────────────────────────────────────────────────────
genai.configure(api_key=settings.GEMINI_API_KEY)


# ─── Document-type-specific prompts ────────────────────────────────────────────
DOCUMENT_PROMPTS = {
    'aadhaar': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid Indian Aadhaar Card (issued by UIDAI).

Look for:
- "Aadhaar" or "आधार" text, UIDAI logo
- A 12-digit Aadhaar number
- The cardholder's full name (in English or Hindi)
- Date of birth or year of birth
- Address (optional)

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "aadhaar",
  "extracted_name": "Full name from the card or null",
  "aadhaar_last4": "Last 4 digits of Aadhaar or null",
  "dob": "DOB if visible or null",
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'income_cert': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid Indian Income Certificate issued by a government authority (Tehsildar, District Magistrate, Sub-Divisional Officer, etc.).

Look for:
- Official government header or seal
- Applicant's full name (may be the student OR their father/mother as head of family)
- Father's name or husband's name if mentioned
- Annual income amount (in rupees)
- Issuing authority name and signature
- Certificate number or reference

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "income_certificate",
  "extracted_name": "Full name of the main applicant on certificate or null",
  "extracted_father_name": "Father's name or husband's name if mentioned, else null",
  "income_amount": numeric annual income in rupees or null,
  "issuing_authority": "Name of issuing office or null",
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'caste_cert': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid Indian Caste Certificate issued by a government authority.

Look for:
- Official government header or seal
- Applicant's full name
- Caste / sub-caste name
- Category (SC / ST / OBC / EWS)
- Issuing authority signature or stamp

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "caste_certificate",
  "extracted_name": "Full name of applicant or null",
  "caste_category": "SC or ST or OBC or EWS or General or null",
  "caste_name": "Name of caste/sub-caste or null",
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'disability_cert': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid Indian Disability Certificate issued by a medical authority or government body (e.g., Civil Surgeon, Medical Board).

Look for:
- Official hospital or government header
- Applicant's full name
- Type of disability
- Disability percentage (e.g., 40%)
- Doctor/authority signature and seal

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "disability_certificate",
  "extracted_name": "Full name of applicant or null",
  "disability_type": "Type of disability or null",
  "disability_percentage": numeric percentage or null,
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'marksheet_10': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid 10th class (Secondary School Certificate / SSC / Matriculation) marksheet issued by an Indian education board (CBSE, ICSE, State Board, etc.).

Look for:
- Board name (CBSE / ICSE / State Board name)
- "Class 10" or "Secondary" or "Matriculation" or "X" or "SSC" mention
- Student's full name
- Roll number
- Subject-wise marks or total percentage / CGPA

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "marksheet_10th",
  "extracted_name": "Full name of student or null",
  "board_name": "Name of board or null",
  "percentage": numeric percentage or CGPA or null,
  "pass_year": year of examination or null,
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'marksheet_12': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid 12th class (Higher Secondary Certificate / HSC / Intermediate / Senior Secondary) marksheet issued by an Indian education board.

Look for:
- Board name (CBSE / ICSE / State Board name)
- "Class 12" or "Higher Secondary" or "Intermediate" or "XII" or "HSC" mention
- Student's full name
- Roll number
- Subject-wise marks or total percentage / CGPA

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "marksheet_12th",
  "extracted_name": "Full name of student or null",
  "board_name": "Name of board or null",
  "percentage": numeric percentage or CGPA or null,
  "pass_year": year of examination or null,
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'current_marksheet': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid current academic year marksheet or result card from a college/university in India (UG, PG, Diploma, etc.).

Look for:
- University or college name
- Student's full name
- Semester or year information
- Subject marks or CGPA / percentage
- Any official stamp or signature

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "current_marksheet",
  "extracted_name": "Full name of student or null",
  "institution_name": "College or university name or null",
  "semester_year": "Semester or year (e.g., 3rd Semester) or null",
  "cgpa_or_percentage": numeric value or null,
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'bank_passbook': """
You are a document verification AI for an Indian government scholarship platform.

Carefully analyze this image. Determine if it is a valid Indian bank passbook front page or account statement showing account holder details.

Look for:
- Bank name and branch details
- Account holder's full name
- Account number (full or partially visible)
- IFSC code
- Any bank stamp or seal

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "bank_passbook",
  "extracted_name": "Account holder's name or null",
  "bank_name": "Name of bank or null",
  "account_number_visible": true or false,
  "rejection_reason": "Reason if not valid, else null"
}
""",

    'photo': """
You are a document verification AI.

Analyze this image. Determine if it is a clear passport-size photograph of a single person. A valid passport photo should:
- Show a person's face clearly (front-facing)
- Have a plain or light background
- Not be a group photo, scenery, document, screenshot, or cartoon

Respond ONLY with a valid JSON object and no other text:
{
  "is_valid": true or false,
  "document_type": "passport_photo",
  "extracted_name": null,
  "face_visible": true or false,
  "rejection_reason": "Reason if not valid (e.g., not a face photo, group photo, blurry) or null"
}
""",
}


# ─── Name matching helper ───────────────────────────────────────────────────────
def names_match(extracted_name: str, *candidate_names) -> bool:
    """
    Fuzzy name match — checks if extracted_name matches ANY of the candidate names.
    Used to match student name, but for income certs also falls back to father/mother name.
    At least 1 significant word (len > 2) must be common.
    """
    if not extracted_name:
        return False
    extracted_words = set(extracted_name.lower().split())
    for candidate in candidate_names:
        if not candidate:
            continue
        candidate_words = set(candidate.lower().split())
        common = [w for w in extracted_words & candidate_words if len(w) > 2]
        if len(common) >= 1:
            return True
    return False


# ─── Core verifier function ─────────────────────────────────────────────────────
def verify_document(doc_instance, student_name: str, father_name: str = '', mother_name: str = '') -> dict:
    """
    Verifies a StudentDocument using Gemini Vision API.

    Args:
        doc_instance: A StudentDocument model instance (with .file and .document_type)
        student_name: Student's full_name from their profile
        father_name:  Father's name (used for income_cert matching)
        mother_name:  Mother's name (used for income_cert matching)

    Returns:
        dict with keys: is_valid, name_matched, verification_status, gemini_result
    """
    doc_type = doc_instance.document_type
    prompt = DOCUMENT_PROMPTS.get(doc_type)

    if not prompt:
        # Unknown doc type — mark as not applicable
        doc_instance.verification_status = 'not_applicable'
        doc_instance.verification_result = {'note': 'No verification prompt for this document type'}
        doc_instance.save()
        return {'is_valid': False, 'name_matched': False, 'verification_status': 'not_applicable'}

    try:
        # ── Read the file ──
        file_path = doc_instance.file.path
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        # ── Determine mime type ──
        file_name = doc_instance.file.name.lower()
        if file_name.endswith('.pdf'):
            # For PDFs: convert first page to image using Pillow (basic) or just send bytes
            mime_type = 'application/pdf'
        elif file_name.endswith('.png'):
            mime_type = 'image/png'
        elif file_name.endswith('.jpg') or file_name.endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif file_name.endswith('.webp'):
            mime_type = 'image/webp'
        else:
            mime_type = 'image/jpeg'  # fallback

        # ── Call Gemini ──
        model = genai.GenerativeModel('gemini-2.5-flash')
        image_part = {'mime_type': mime_type, 'data': file_bytes}
        response = model.generate_content([prompt.strip(), image_part])

        raw_text = response.text.strip()

        # ── Parse JSON from response ──
        # Strip markdown code fences if present
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            gemini_result = json.loads(json_match.group())
        else:
            raise ValueError(f"No JSON found in Gemini response: {raw_text}")

        is_valid = gemini_result.get('is_valid', False)
        extracted_name = gemini_result.get('extracted_name')
        extracted_father = gemini_result.get('extracted_father_name')

        # ── Name check (skip for passport photo) ──
        if doc_type == 'photo':
            name_matched = True  # No name check for passport photo
        elif doc_type == 'income_cert':
            # Income certs may be in parent's name — match student OR father OR mother
            name_matched = (
                names_match(extracted_name, student_name, father_name, mother_name)
                or names_match(extracted_father, student_name, father_name, mother_name)
            )
        elif extracted_name:
            name_matched = names_match(extracted_name, student_name)
        else:
            name_matched = False

        # ── Determine final status ──
        if is_valid and (doc_type == 'photo' or name_matched):
            final_status = 'verified'
            doc_instance.is_verified = True
        else:
            final_status = 'failed'
            doc_instance.is_verified = False
            # Add name mismatch note to result
            if is_valid and not name_matched:
                gemini_result['rejection_reason'] = (
                    f"Name mismatch: Document shows '{extracted_name}' but "
                    f"could not match student ('{student_name}')"
                    + (f", father ('{father_name}')", '')[not father_name]
                    + (f" or mother ('{mother_name}')", '')[not mother_name]
                )

        doc_instance.verification_status = final_status
        doc_instance.verification_result = gemini_result
        doc_instance.save()

        return {
            'is_valid': is_valid,
            'name_matched': name_matched,
            'verification_status': final_status,
            'gemini_result': gemini_result,
        }

    except Exception as e:
        error_result = {
            'is_valid': False,
            'rejection_reason': f'Verification error: {str(e)}',
        }
        doc_instance.verification_status = 'failed'
        doc_instance.is_verified = False
        doc_instance.verification_result = error_result
        doc_instance.save()

        return {
            'is_valid': False,
            'name_matched': False,
            'verification_status': 'failed',
            'gemini_result': error_result,
        }
