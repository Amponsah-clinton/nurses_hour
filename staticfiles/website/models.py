from django.db import models
from django.conf import settings
from django.utils import timezone


class Visit(models.Model):
    """One record per home page view for 24h visit count."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']


class UserProfile(models.Model):
    """Stores phone, program, and other profile data for auth (login with email or phone)."""
    PROGRAM_CHOICES = [
        ('', '-- Select program --'),
        ('general', 'General Nursing'),
        ('midwifery', 'Midwifery'),
        ('community', 'Community Nursing'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(max_length=10, blank=True, db_index=True)
    program = models.CharField(
        max_length=20,
        choices=PROGRAM_CHOICES,
        default='',
        blank=True,
        help_text='Nursing program the student is enrolled in.',
    )

    def __str__(self):
        return f"{self.user.email} ({self.phone or 'no phone'})"


class MCQQuestion(models.Model):
    """Multiple choice question for practice banks. Synced to Supabase."""
    PROGRAM_CHOICES = [
        ('rgn', 'Registered General Nursing (RGN)'),
        ('rm', 'Registered Midwifery (RM)'),
        ('rcn', 'Registered Community Nursing (RCN)'),
    ]
    PAPER_CHOICES = [
        # RGN
        ('rgn_med_surg', 'RGN – Medical–Surgical Nursing'),
        ('rgn_community_health', 'RGN – Community Health Nursing'),
        ('rgn_general', 'RGN – General Nursing Paper'),
        # RM
        ('rm_midwifery_obstetrics', 'RM – Midwifery & Obstetrics'),
        ('rm_community_based', 'RM – Community-Based Midwifery'),
        ('rm_general', 'RM – General Midwifery Paper'),
        # RCN
        ('rcn_community_phc', 'RCN – Community Health & Primary Health Care'),
        ('rcn_maternal_child', 'RCN – Maternal & Child Health'),
        ('rcn_general', 'RCN – General Community Nursing Paper'),
    ]
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    CORRECT_CHOICES = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    correct_answer = models.CharField(max_length=1, choices=CORRECT_CHOICES)
    answer_explanation = models.TextField(blank=True, help_text='Optional rationale for the correct answer.')
    program = models.CharField(
        max_length=10,
        choices=PROGRAM_CHOICES,
        blank=True,
        default='',
        help_text='Which nursing programme this question belongs to (RGN, RM, or RCN).',
    )
    paper = models.CharField(
        max_length=40,
        choices=PAPER_CHOICES,
        blank=True,
        default='',
        help_text='Specific written paper (e.g. Medical–Surgical, Community Health, General Paper).',
    )
    topic = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class CaseStudy(models.Model):
    """Case study for clinical reasoning. Synced to Supabase. file_url = case_study bucket or external link."""
    title = models.CharField(max_length=255)
    scenario = models.TextField(blank=True)
    content = models.TextField(blank=True)
    file_url = models.URLField(blank=True, max_length=500, help_text='Optional: Supabase case_study bucket URL or external link')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class BookOrSlide(models.Model):
    """Book or slide resource. file_url = Supabase Storage URL or link. Synced to Supabase."""
    KIND_CHOICES = [('book', 'Book'), ('slide', 'Slide')]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file_url = models.URLField(blank=True, max_length=500)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Payment(models.Model):
    """Payment record. Synced to Supabase."""
    STATUS_CHOICES = [('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded')]
    user_email = models.EmailField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Inquiry(models.Model):
    """Contact form submission. Synced to Supabase. Admin can reply via email."""
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Inquiries'


class CaseStudyAccess(models.Model):
    """Which case studies a student has purchased/unlocked."""
    user_email = models.EmailField(db_index=True)
    case_study = models.ForeignKey(CaseStudy, on_delete=models.CASCADE, related_name='accesses')
    payment = models.ForeignKey('Payment', null=True, blank=True, on_delete=models.SET_NULL, related_name='case_study_accesses')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user_email', 'case_study')


class ResourceBookmark(models.Model):
    """Books/lecture notes a student has saved/bookmarked."""
    user_email = models.EmailField(db_index=True)
    resource = models.ForeignKey(BookOrSlide, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user_email', 'resource')


class PracticeSession(models.Model):
    """A practice run (set of MCQ questions) for a student."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='practice_sessions')
    program = models.CharField(max_length=10, blank=True, default='')
    paper = models.CharField(max_length=40, blank=True, default='')
    timed = models.BooleanField(default=False, help_text='If true, student practiced under timed conditions (50s per question).')
    total_questions = models.PositiveIntegerField()
    correct_count = models.PositiveIntegerField(default=0)
    questions = models.JSONField(default=list, help_text='List of MCQQuestion IDs for this session in order.')
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']


class PracticeAnswer(models.Model):
    """An answer to a single MCQ question within a practice session."""
    session = models.ForeignKey(PracticeSession, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='practice_answers')
    question = models.ForeignKey(MCQQuestion, on_delete=models.CASCADE, related_name='practice_answers')
    chosen_answer = models.CharField(max_length=1, choices=MCQQuestion.CORRECT_CHOICES)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    order_index = models.PositiveIntegerField(help_text='1-based index within the session.')

    class Meta:
        ordering = ['order_index']
        unique_together = ('session', 'question')

