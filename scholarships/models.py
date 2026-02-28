from django.db import models
import json


# ─────────────────────────────────────────────────────────────────────────────
# CHOICE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

EDUCATION_LEVEL_CHOICES = [
    ('HIGH_SCHOOL', 'High School (9th–12th)'),
    ('DIPLOMA',     'Diploma'),
    ('UG',          'Undergraduate (B.Tech / BA / B.Sc etc.)'),
    ('PG',          'Postgraduate (M.Tech / MBA / M.Sc etc.)'),
    ('PHD',         'Doctorate / Ph.D'),
    ('ANY',         'Any Level'),
]

DISTRIBUTION_TYPE_CHOICES = [
    ('FIXED',   'Fixed Amount per Winner'),
    ('DYNAMIC', 'Proportional / Dynamic Allocation'),
]

DISBURSEMENT_METHOD_CHOICES = [
    ('BANK_TRANSFER', 'Direct Bank Transfer (Razorpay Route)'),
    ('VOUCHER',       'Educational Vouchers Only'),
]

VERIFICATION_STRICTNESS_CHOICES = [
    ('STANDARD', 'Standard – Manual Upload'),
    ('STRICT',   'Strict – DigiLocker / Govt API Verified'),
]

DOCUMENT_CHOICES = [
    ('income_certificate',  'Income Certificate'),
    ('marksheet',           'Previous Year Marksheet'),
    ('college_id',          'College ID / Bonafide Certificate'),
    ('aadhaar',             'Aadhaar Card'),
    ('caste_certificate',   'Caste Certificate'),
    ('bank_passbook',       'Bank Passbook'),
    ('disability_cert',     'Disability Certificate'),
    ('domicile_certificate','Domicile Certificate'),
    ('photo',               'Passport Size Photo'),
]


# ─────────────────────────────────────────────────────────────────────────────
# SCHOLARSHIP MODEL  (complete rewrite)
# ─────────────────────────────────────────────────────────────────────────────

class Scholarship(models.Model):
    """
    Master model for a funded scholarship created by an Organization.
    Stays inactive (is_active=False) until full payment is confirmed via Razorpay.
    """

    # ── BASICS ──────────────────────────────────────────────────────────────
    title = models.CharField(max_length=255, unique=True, verbose_name="Scholarship Title")
    org_profile = models.ForeignKey(
        'users.OrganizationProfile',
        on_delete=models.CASCADE,
        related_name='scholarships',
        null=True, blank=True,
        verbose_name="Organization"
    )
    logo = models.ImageField(
        upload_to='scholarship_logos/',
        blank=True, null=True,
        verbose_name="Organization Logo"
    )
    description = models.TextField(verbose_name="About the Scholarship (HTML allowed)")
    deadline = models.DateTimeField(verbose_name="Application Deadline")

    # ── ELIGIBILITY ─────────────────────────────────────────────────────────
    education_level = models.CharField(
        max_length=20,
        choices=EDUCATION_LEVEL_CHOICES,
        default='ANY',
        verbose_name="Target Education Level"
    )
    # Stored as a JSON list e.g. ["B.Tech", "MBBS", "BA"]
    courses = models.TextField(
        blank=True, default='[]',
        help_text='JSON list of eligible courses/streams. Leave "[]" for any.'
    )
    max_family_income = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Max Family Annual Income (₹)",
        help_text="Maximum annual family income in INR (e.g. 800000 for ₹8 lakh)"
    )
    min_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Minimum Academic Score (%/CGPA)"
    )
    # Stored as a JSON list e.g. ["women", "tier2", "SC", "disabled"]
    demographic_focus = models.TextField(
        blank=True, default='[]',
        help_text='JSON list of demographic targets. Leave "[]" for all.'
    )

    # ── FINANCIALS ──────────────────────────────────────────────────────────
    total_budget = models.PositiveIntegerField(
        verbose_name="Total Budget (₹)",
        help_text="Full amount the organization deposits into escrow (INR)",
        null=True,
        blank=True,
    )
    distribution_type = models.CharField(
        max_length=10,
        choices=DISTRIBUTION_TYPE_CHOICES,
        default='FIXED',
        verbose_name="Distribution Logic"
    )
    fixed_amount = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Fixed Amount per Winner (₹)",
        help_text="Required when distribution type is FIXED"
    )
    num_winners = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Number of Winners",
        help_text="How many students get selected"
    )
    disbursement_method = models.CharField(
        max_length=20,
        choices=DISBURSEMENT_METHOD_CHOICES,
        default='BANK_TRANSFER',
        verbose_name="Disbursement Method"
    )

    # ── PLATFORM FILTERS ────────────────────────────────────────────────────
    min_karma = models.PositiveIntegerField(
        default=0,
        verbose_name="Minimum Karma Points Required",
        help_text="Only students with ≥ this karma can apply"
    )
    verification_strictness = models.CharField(
        max_length=10,
        choices=VERIFICATION_STRICTNESS_CHOICES,
        default='STANDARD',
        verbose_name="Verification Strictness"
    )
    essay_question = models.TextField(
        blank=True,
        verbose_name="Custom Essay / Question (Optional)",
        help_text="e.g. 'Why do you need this scholarship?'"
    )

    # ── STATUS / META ────────────────────────────────────────────────────────
    is_active = models.BooleanField(
        default=False,
        help_text="Becomes True only after payment is confirmed"
    )
    is_funded = models.BooleanField(
        default=False,
        help_text="True once Razorpay payment is verified"
    )
    # ── Application close control ────────────────────────────────────────────
    applications_closed = models.BooleanField(
        default=False,
        help_text="Org can manually close applications before deadline"
    )
    closed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp when org manually closed applications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    # ── LEGACY FIELDS (kept for backward compatibility) ──────────────────────
    # These were on the old model and referenced in existing views/templates.
    # They are nullable so old data isn't broken.
    organization = models.CharField(
        max_length=255, blank=True,
        help_text="[Legacy] Organization name as string. Use org_profile FK instead."
    )
    source_url = models.URLField(max_length=2000, blank=True)
    award_amount = models.CharField(
        max_length=50, blank=True,
        help_text="[Legacy] Free-text award amount. Use total_budget instead."
    )
    details = models.TextField(
        blank=True,
        help_text="[Legacy] Use description instead."
    )
    is_verified = models.BooleanField(default=False)
    found_by_student = models.ForeignKey(
        'users.StudentProfile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='found_scholarships'
    )
    finder_karma_awarded = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    # ── HELPERS ─────────────────────────────────────────────────────────────
    def get_courses(self):
        """Return courses as Python list."""
        try:
            return json.loads(self.courses)
        except (ValueError, TypeError):
            return []

    def set_courses(self, course_list):
        self.courses = json.dumps(course_list)

    def get_demographic_focus(self):
        """Return demographic_focus as Python list."""
        try:
            return json.loads(self.demographic_focus)
        except (ValueError, TypeError):
            return []

    def set_demographic_focus(self, demo_list):
        self.demographic_focus = json.dumps(demo_list)

    @property
    def name(self):
        """
        Backward-compatibility alias for `title`.
        All existing templates and views use scholarship.name — this keeps
        them working without any changes.
        """
        return self.title

    def computed_award_display(self):
        """Human-readable award amount for template display."""
        if self.distribution_type == 'FIXED' and self.fixed_amount and self.num_winners:
            return f"₹{self.fixed_amount:,} × {self.num_winners} winners"
        return f"₹{self.total_budget:,} (Dynamic)"


# ─────────────────────────────────────────────────────────────────────────────
# SCHOLARSHIP FUNDING LEDGER  (Razorpay escrow record)
# ─────────────────────────────────────────────────────────────────────────────

class ScholarshipFunding(models.Model):
    """
    Tracks the Razorpay payment lifecycle for a scholarship's escrow deposit.
    Created when org reaches the payment step; updated on callback.
    """

    FUNDING_STATUS_CHOICES = [
        ('PENDING',   'Pending Payment'),
        ('PAID',      'Paid – In Escrow'),
        ('DISBURSED', 'Disbursed to Winners'),
        ('REFUNDED',  'Refunded'),
    ]

    scholarship = models.OneToOneField(
        Scholarship,
        on_delete=models.CASCADE,
        related_name='funding'
    )
    razorpay_order_id   = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=255, blank=True)
    # Amount in paise (multiply INR by 100)
    amount_paise = models.PositiveIntegerField(
        default=0,
        help_text="Amount in paise (INR × 100)"
    )
    status = models.CharField(
        max_length=10,
        choices=FUNDING_STATUS_CHOICES,
        default='PENDING'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    paid_at     = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Funding for '{self.scholarship.title}' — {self.get_status_display()}"

    @property
    def amount_inr(self):
        return self.amount_paise // 100


# ─────────────────────────────────────────────────────────────────────────────
# ELIGIBILITY CRITERIA  (kept for legacy + future AI engine)
# ─────────────────────────────────────────────────────────────────────────────

class EligibilityCriteria(models.Model):
    """
    Flexible key-value eligibility rules for the recommendation engine.
    The structured eligibility fields live directly on Scholarship for
    simple querying; this model is for extensible/custom rules.
    """
    OPERATOR_CHOICES = [('GT', '>'), ('LT', '<'), ('EQ', '='), ('IN', 'IN')]

    scholarship = models.ForeignKey(
        Scholarship, on_delete=models.CASCADE, related_name='eligibility_criteria'
    )
    criterion_type = models.CharField(
        max_length=50,
        help_text="e.g. 'MIN_INCOME', 'MAX_AGE', 'MIN_GPA', 'STATE'"
    )
    comparison_operator = models.CharField(
        max_length=2, choices=OPERATOR_CHOICES, default='GT'
    )
    value = models.CharField(max_length=255)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.scholarship.title}: {self.criterion_type} {self.comparison_operator} {self.value}"


# ─────────────────────────────────────────────────────────────────────────────
# REQUIRED DOCUMENT  (documents org mandates for application)
# ─────────────────────────────────────────────────────────────────────────────

class RequiredDocument(models.Model):
    """
    Documents that a student must upload when applying for a scholarship.
    Populated by the org during scholarship creation (Step 4).
    """
    scholarship = models.ForeignKey(
        Scholarship, on_delete=models.CASCADE, related_name='required_documents'
    )
    document_name = models.CharField(
        max_length=100,
        choices=DOCUMENT_CHOICES,
        help_text="Identifier key for the document type"
    )
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    verification_strictness = models.CharField(
        max_length=10,
        choices=VERIFICATION_STRICTNESS_CHOICES,
        default='STANDARD',
        verbose_name="Verification Method for this document"
    )

    def __str__(self):
        return f"{self.get_document_name_display()} — {self.scholarship.title}"


# ─────────────────────────────────────────────────────────────────────────────
# MARKSHEET VERIFICATION  (Phase 7 — Award Engine)
# ─────────────────────────────────────────────────────────────────────────────

class MarksheetVerification(models.Model):
    """
    Stores a student's last semester marksheet and Gemini-extracted academic score.
    Created / updated during OTR Step 7.
    """
    student = models.OneToOneField(
        'users.StudentProfile',
        on_delete=models.CASCADE,
        related_name='marksheet_verification'
    )
    marksheet_file = models.FileField(
        upload_to='otr/marksheets/%Y/%m/',
        verbose_name="Last Semester Marksheet"
    )
    # Gemini-extracted fields
    last_sem_marks = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Last Semester Marks (%)",
        help_text="Percentage extracted by Gemini from the marksheet"
    )
    extracted_institution = models.CharField(
        max_length=255, blank=True,
        help_text="Institution name as extracted by Gemini"
    )
    extracted_semester = models.CharField(
        max_length=50, blank=True,
        help_text="Semester / year as extracted by Gemini"
    )
    extracted_student_name = models.CharField(
        max_length=150, blank=True,
        help_text="Student name as extracted by Gemini"
    )
    gemini_verified = models.BooleanField(
        default=False,
        help_text="True when Gemini extraction matched the student profile"
    )
    raw_gemini_response = models.TextField(
        blank=True,
        help_text="Raw JSON response from Gemini for audit purposes"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Marksheet Verification"

    def __str__(self):
        return f"{self.student} — {self.last_sem_marks}% (verified: {self.gemini_verified})"


# ─────────────────────────────────────────────────────────────────────────────
# FEES VERIFICATION  (Phase 7 — Award Engine)
# ─────────────────────────────────────────────────────────────────────────────

class FeesVerification(models.Model):
    """
    Stores a student's college fees receipt and Gemini-extracted fees amount.
    College name on receipt is cross-checked against the student's AcademicRecord.
    Created / updated during OTR Step 7.
    """
    student = models.OneToOneField(
        'users.StudentProfile',
        on_delete=models.CASCADE,
        related_name='fees_verification'
    )
    fees_receipt_file = models.FileField(
        upload_to='otr/fees_receipts/%Y/%m/',
        verbose_name="College Fees Receipt"
    )
    # Gemini-extracted fields
    total_annual_fees = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Total Annual Fees (Rs.)",
        help_text="Fees amount extracted by Gemini from the receipt"
    )
    extracted_college_name = models.CharField(
        max_length=255, blank=True,
        help_text="College/institution name as extracted by Gemini"
    )
    extracted_student_name = models.CharField(
        max_length=150, blank=True,
        help_text="Student name as extracted by Gemini"
    )
    extracted_academic_year = models.CharField(
        max_length=20, blank=True,
        help_text="Academic year extracted from the receipt (e.g. 2023-24)"
    )
    college_match = models.BooleanField(
        default=False,
        help_text="True when receipt college name matches the student's registered institution"
    )
    gemini_verified = models.BooleanField(
        default=False,
        help_text="True when Gemini successfully extracted and matched receipt data"
    )
    raw_gemini_response = models.TextField(
        blank=True,
        help_text="Raw JSON response from Gemini for audit purposes"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Fees Verification"

    def __str__(self):
        return f"{self.student} — Rs.{self.total_annual_fees} (college match: {self.college_match})"


# ─────────────────────────────────────────────────────────────────────────────
# SCHOLARSHIP AWARD  (Phase 7 — Award Engine)
# ─────────────────────────────────────────────────────────────────────────────

class ScholarshipAward(models.Model):
    """
    Created for each student who wins a scholarship.
    Tracks the full lifecycle from merit-list approval to bank transfer completion.
    """

    TRANSFER_STATUS_CHOICES = [
        ('PENDING',    'Pending Approval'),
        ('APPROVED',   'Approved by Organisation'),
        ('PROCESSING', 'Bank Transfer Initiated'),
        ('DONE',       'Transfer Completed'),
        ('FAILED',     'Transfer Failed — Retry Needed'),
    ]

    application = models.OneToOneField(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='award'
    )
    scholarship = models.ForeignKey(
        Scholarship,
        on_delete=models.CASCADE,
        related_name='awards'
    )
    student = models.ForeignKey(
        'users.StudentProfile',
        on_delete=models.CASCADE,
        related_name='awards'
    )

    # Merit calculation snapshot (stored at award time so record is self-contained)
    merit_score      = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    merit_rank       = models.PositiveIntegerField(default=0)
    marks_at_award   = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="last_sem_marks at the time of award"
    )
    fees_at_award    = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="total_annual_fees at the time of award"
    )
    prior_received   = models.PositiveIntegerField(
        default=0,
        help_text="Total scholarship Rs. received before this award (for need score)"
    )

    # Award financials
    amount_awarded   = models.PositiveIntegerField(
        default=0,
        verbose_name="Amount Awarded (Rs.)"
    )

    # Transfer tracking
    transfer_status  = models.CharField(
        max_length=12,
        choices=TRANSFER_STATUS_CHOICES,
        default='PENDING'
    )
    razorpay_payout_id = models.CharField(max_length=100, blank=True)
    transfer_ref       = models.CharField(
        max_length=255, blank=True,
        help_text="Razorpay payout reference or UTR number"
    )
    transfer_initiated_at = models.DateTimeField(null=True, blank=True)
    transfer_completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason        = models.TextField(blank=True)

    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['merit_rank']
        verbose_name = "Scholarship Award"

    def __str__(self):
        return (
            f"Award #{self.merit_rank}: {self.student} — "
            f"{self.scholarship.title} — Rs.{self.amount_awarded} ({self.transfer_status})"
        )

    @property
    def is_bank_transfer(self):
        return self.scholarship.disbursement_method == 'BANK_TRANSFER'

    @property
    def coverage_before(self):
        """Scholarship coverage % before this award."""
        if self.fees_at_award:
            return round((self.prior_received / self.fees_at_award) * 100, 1)
        return 0
