import csv
import json
import io

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import OperationalError, models
from datetime import timedelta
from django.template.loader import render_to_string
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .forms import SignUpForm, LoginForm, AdminMCQForm, AdminCaseStudyForm, AdminBookSlideForm, AdminPaymentForm, ProfileForm, SupportForm
from .models import Visit, MCQQuestion, CaseStudy, BookOrSlide, Payment, Inquiry, CaseStudyAccess, ResourceBookmark, UserProfile, PracticeSession, PracticeAnswer

# Programme & paper metadata for student practice
PROGRAM_FROM_PROFILE = {
    'general': 'rgn',
    'midwifery': 'rm',
    'community': 'rcn',
}

PROGRAM_LABELS = {
    'rgn': 'Registered General Nursing (RGN)',
    'rm': 'Registered Midwifery (RM)',
    'rcn': 'Registered Community Nursing (RCN)',
}

PAPER_CONFIG = {
    'rgn': [
        {
            'code': 'rgn_med_surg',
            'title': 'Medical–Surgical Nursing',
            'description': 'Covers adult medical and surgical conditions, perioperative care, and nursing management.',
        },
        {
            'code': 'rgn_community_health',
            'title': 'Community Health Nursing',
            'description': 'Focus on public health, health promotion, disease prevention, and community interventions.',
        },
        {
            'code': 'rgn_general',
            'title': 'General Nursing Paper',
            'description': 'Fundamentals, ethics, pharmacology, nutrition, psychology and core nursing concepts.',
        },
    ],
    'rm': [
        {
            'code': 'rm_midwifery_obstetrics',
            'title': 'Midwifery & Obstetrics',
            'description': 'Pregnancy, labour, puerperium, obstetric emergencies and newborn care.',
        },
        {
            'code': 'rm_community_based',
            'title': 'Community-Based Midwifery',
            'description': 'Community and primary care in maternal and newborn health.',
        },
        {
            'code': 'rm_general',
            'title': 'General Midwifery Paper',
            'description': 'Maternal health, newborn care, family planning and complications.',
        },
    ],
    'rcn': [
        {
            'code': 'rcn_community_phc',
            'title': 'Community Health & Primary Health Care',
            'description': 'Primary health care principles, outreach, and community diagnosis.',
        },
        {
            'code': 'rcn_maternal_child',
            'title': 'Maternal & Child Health',
            'description': 'Antenatal, postnatal, under‑five clinics and growth monitoring.',
        },
        {
            'code': 'rcn_general',
            'title': 'General Community Nursing Paper',
            'description': 'Health promotion, sanitation, disease prevention and basic epidemiology.',
        },
    ],
}

PAPER_LABELS = {item['code']: item['title'] for plist in PAPER_CONFIG.values() for item in plist}

User = get_user_model()


def _is_admin_user(user):
    return user and user.is_authenticated and getattr(settings, 'ADMIN_EMAIL', None) and user.email == settings.ADMIN_EMAIL


def redirect_to_dashboard(user):
    """Send admin to admin dashboard, everyone else to user dashboard."""
    next_url = settings.LOGIN_REDIRECT_URL
    if _is_admin_user(user):
        next_url = reverse('website:admin_dashboard')
    return redirect(next_url)


def _get_landing_stats():
    """Visits in 24h = count + 100. Users = 1000 + User.count(). Safe when DB is missing/unmigrated (e.g. Vercel /tmp)."""
    try:
        since = timezone.now() - timedelta(hours=24)
        visits_24h = Visit.objects.filter(created_at__gte=since).count()
        users_count = User.objects.count()
        return {
            'visits_display': visits_24h + 100,
            'users_display': 1000 + users_count,
        }
    except OperationalError:
        return {'visits_display': 100, 'users_display': 1000}


def home(request):
    if request.method == 'GET':
        try:
            Visit.objects.create()
        except OperationalError:
            pass  # DB may be read-only or tables missing (e.g. Vercel /tmp)
    stats = _get_landing_stats()
    return render(request, 'website/index.html', stats)


def landing_stats(request):
    """JSON endpoint for live stats (visits 24h + 100, users 1000 + count)."""
    return JsonResponse(_get_landing_stats())


def courses(request):
    return render(request, 'website/courses.html')


def event(request):
    return render(request, 'website/event.html')


def event_details(request):
    return render(request, 'website/event_details.html')


def admissions(request):
    return render(request, 'website/admissions.html')


def elements(request):
    return render(request, 'website/elements.html')


def contact(request):
    return render(request, 'website/contact.html')


def contact_submit(request):
    if request.method != 'POST':
        return redirect('website:contact')
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    subject = request.POST.get('subject', '').strip()
    message = request.POST.get('message', '').strip()
    if not name or not email or not message:
        messages.error(request, 'Please fill in name, email, and message.')
        return redirect('website:contact')
    inquiry = Inquiry.objects.create(name=name, email=email, subject=subject, message=message)
    try:
        from .supabase_sync import sync_inquiry_to_supabase
        sync_inquiry_to_supabase(inquiry)
    except Exception:
        pass
    notify_email = getattr(settings, 'INQUIRY_NOTIFY_EMAIL', None) or settings.ADMIN_EMAIL
    if notify_email:
        try:
            html = render_to_string('email/new_inquiry_notification.html', {
                'name': name,
                'email': email,
                'subject': subject or '—',
                'message': message,
            })
            send_mail(
                subject=f"[NurseHour] New inquiry from {name}",
                message=f"From: {name} <{email}>\nSubject: {subject or '—'}\n\n{message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notify_email],
                fail_silently=False,
                html_message=html,
            )
        except Exception:
            pass
    messages.success(request, 'Your message has been sent. We’ll get back to you soon.')
    return redirect('website:contact')


def signup(request):
    if request.user.is_authenticated:
        return redirect('website:home')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower()
        name = form.cleaned_data['name'] or ''
        password = form.cleaned_data['password']
        phone = form.cleaned_data.get('phone') or ''
        program = form.cleaned_data.get('program') or ''
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name,
            password=password,
        )
        from .models import UserProfile
        UserProfile.objects.create(user=user, phone=phone, program=program)
        try:
            from .supabase_sync import sync_user_to_supabase
            sync_user_to_supabase(user)
        except Exception:
            pass
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, f'Welcome, {name or email}! Your account has been created.')
        return redirect_to_dashboard(user)
    return render(request, 'website/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect_to_dashboard(request.user)
    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email_or_phone = form.cleaned_data['email_or_phone']
            password = form.cleaned_data['password']
            user = None
            if '@' in email_or_phone:
                user = User.objects.filter(email=email_or_phone).first()
            else:
                from .models import UserProfile
                profile = UserProfile.objects.filter(phone=email_or_phone).select_related('user').first()
                if profile:
                    user = profile.user
            if user and user.check_password(password):
                auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'Welcome back, {user.get_short_name() or user.email}!')
                return redirect_to_dashboard(user)
            form.add_error(None, 'Invalid email/phone or password.')
        else:
            form.add_error(None, 'Please correct the errors below.')
    return render(request, 'website/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('website:home')


def admin_required(view_func):
    """Restrict view to hardcoded admin email only."""
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL + '?next=' + request.path)
        if not _is_admin_user(request.user):
            return redirect('website:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapped


@login_required
def dashboard(request):
    """User dashboard: practice, case studies, resources, profile. Admins are sent to admin_dashboard."""
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    profile = getattr(request.user, 'profile', None)
    profile_program = getattr(profile, 'program', '') or ''
    program_code = PROGRAM_FROM_PROFILE.get(profile_program, '')
    program_label = PROGRAM_LABELS.get(program_code, '')
    papers = PAPER_CONFIG.get(program_code or 'rgn', PAPER_CONFIG.get('rgn', []))
    context = {
        'user_program_code': program_code,
        'user_program_label': program_label,
        'practice_papers': papers,
    }
    return render(request, 'website/dashboard.html', context)


@login_required
def practice(request):
    """Practice setup: choose programme, paper, timed/untimed and number of questions."""
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    profile = getattr(request.user, 'profile', None)
    profile_program = getattr(profile, 'program', '') or ''
    default_program = PROGRAM_FROM_PROFILE.get(profile_program, 'rgn')
    if request.method == 'POST':
        program = (request.POST.get('program') or default_program or 'rgn').strip()
        if program not in PROGRAM_LABELS:
            program = 'rgn'
        paper = (request.POST.get('paper') or '').strip()
        available_papers = PAPER_CONFIG.get(program, [])
        paper_codes = [p['code'] for p in available_papers]
        if paper not in paper_codes and paper_codes:
            paper = paper_codes[0]
        timed = bool(request.POST.get('timed'))
        try:
            num_questions = int(request.POST.get('num_questions') or 10)
        except ValueError:
            num_questions = 10
        num_questions = max(1, min(num_questions, 50))
        # Build candidate questions, excluding ones the user has already answered
        answered_ids = PracticeAnswer.objects.filter(user=request.user).values_list('question_id', flat=True)
        qs = MCQQuestion.objects.all()
        if program:
            qs = qs.filter(program=program)
        if paper:
            qs = qs.filter(paper=paper)
        if answered_ids:
            qs = qs.exclude(id__in=answered_ids)
        qs = qs.order_by('?')
        total_available = qs.count()
        if total_available == 0:
            messages.info(request, 'No new questions available for this paper. You have answered all existing questions.')
            return redirect('website:practice')
        take = min(num_questions, total_available)
        question_ids = list(qs.values_list('id', flat=True)[:take])
        session = PracticeSession.objects.create(
            user=request.user,
            program=program,
            paper=paper,
            timed=timed,
            total_questions=take,
            questions=question_ids,
        )
        return redirect('website:practice_session_question', session_id=session.id, index=1)
    # GET – show setup form and recent sessions
    program = default_program
    available_papers = PAPER_CONFIG.get(program, [])
    recent_sessions = PracticeSession.objects.filter(user=request.user).order_by('-started_at')[:5]
    context = {
        'program': program,
        'program_label': PROGRAM_LABELS.get(program, ''),
        'available_programs': PROGRAM_LABELS,
        'available_papers': PAPER_CONFIG,
        'selected_papers': available_papers,
        'recent_sessions': recent_sessions,
    }
    return render(request, 'website/practice_setup.html', context)


@login_required
def practice_session_question(request, session_id, index):
    """Show a single question within a practice session and record the answer."""
    session = get_object_or_404(PracticeSession, id=session_id, user=request.user)
    questions = session.questions or []
    total = len(questions)
    if total == 0:
        return redirect('website:practice')
    try:
        index = int(index)
    except (TypeError, ValueError):
        index = 1
    if index < 1 or index > total:
        return redirect('website:practice_review', session_id=session.id)
    question_id = questions[index - 1]
    question = get_object_or_404(MCQQuestion, id=question_id)
    if request.method == 'POST':
        chosen = (request.POST.get('answer') or '').strip().upper()
        if chosen not in dict(MCQQuestion.CORRECT_CHOICES):
            messages.error(request, 'Please select an answer before continuing.')
            return redirect('website:practice_session_question', session_id=session.id, index=index)
        is_correct = (chosen == question.correct_answer)
        answer, created = PracticeAnswer.objects.update_or_create(
            session=session,
            question=question,
            defaults={
                'user': request.user,
                'chosen_answer': chosen,
                'is_correct': is_correct,
                'order_index': index,
            },
        )
        # Update session score
        correct_count = PracticeAnswer.objects.filter(session=session, is_correct=True).count()
        session.correct_count = correct_count
        # Mark finished when last question is answered
        if index == total and session.finished_at is None:
            session.finished_at = timezone.now()
            try:
                from .supabase_sync import sync_practice_session_to_supabase
                sync_practice_session_to_supabase(session)
            except Exception:
                pass
        session.save(update_fields=['correct_count', 'finished_at'])
        # Sync individual answer to Supabase
        try:
            from .supabase_sync import sync_practice_answer_to_supabase
            sync_practice_answer_to_supabase(answer)
        except Exception:
            pass
        if index >= total:
            return redirect('website:practice_review', session_id=session.id)
        return redirect('website:practice_session_question', session_id=session.id, index=index + 1)
    progress_pct = int((index / float(total)) * 100)
    context = {
        'session': session,
        'question': question,
        'index': index,
        'total': total,
        'progress_pct': progress_pct,
        'timed': session.timed,
        'seconds_per_question': 50,
    }
    return render(request, 'website/practice_run.html', context)


@login_required
def practice_review(request, session_id):
    """Review all questions and answers for a completed practice session."""
    session = get_object_or_404(PracticeSession, id=session_id, user=request.user)
    answers = PracticeAnswer.objects.filter(session=session).select_related('question').order_by('order_index')
    total = session.total_questions
    correct = session.correct_count
    percent = int((correct / float(total)) * 100) if total else 0
    context = {
        'session': session,
        'answers': answers,
        'total': total,
        'correct': correct,
        'percent': percent,
    }
    return render(request, 'website/practice_review.html', context)


@login_required
def practice_history(request):
    """List all past practice sessions and scores for the current student."""
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    sessions = PracticeSession.objects.filter(user=request.user).order_by('-started_at')
    context = {'sessions': sessions}
    return render(request, 'website/practice_history.html', context)


@login_required
def practice_repeat(request, session_id):
    """Start a new practice session with the same questions as a past session."""
    original = get_object_or_404(PracticeSession, id=session_id, user=request.user)
    questions = original.questions or []
    if not questions:
        messages.error(request, 'This session has no questions to repeat.')
        return redirect('website:practice_history')
    new_session = PracticeSession.objects.create(
        user=request.user,
        program=original.program,
        paper=original.paper,
        timed=original.timed,
        total_questions=len(questions),
        questions=questions,
    )
    messages.info(request, 'Started a new session with the same questions.')
    return redirect('website:practice_session_question', session_id=new_session.id, index=1)


@login_required
def case_studies_dashboard(request):
    """Student dashboard – case studies the student owns and all available case studies."""
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    email = (request.user.email or '').strip().lower()
    owned_ids = CaseStudyAccess.objects.filter(user_email=email).values_list('case_study_id', flat=True)
    owned = CaseStudy.objects.filter(id__in=owned_ids)
    all_cases = CaseStudy.objects.all()
    context = {
        'owned_case_studies': owned,
        'all_case_studies': all_cases,
        'owned_ids': set(owned_ids),
    }
    return render(request, 'website/case_studies.html', context)


@login_required
def purchase_case_study(request, pk):
    """Mark a case study as purchased for the current student and create a completed payment record."""
    if request.method != 'POST':
        return redirect('website:case_studies')
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    case = get_object_or_404(CaseStudy, pk=pk)
    email = (request.user.email or '').strip().lower()
    access, created = CaseStudyAccess.objects.get_or_create(
        user_email=email,
        case_study=case,
    )
    if created:
        # Create a zero-amount completed payment record for tracking.
        payment = Payment.objects.create(
            user_email=email,
            amount=0,
            status='completed',
            description=f'Access to case study: {case.title}',
        )
        access.payment = payment
        access.save(update_fields=['payment'])
        try:
            from .supabase_sync import sync_payment_to_supabase
            sync_payment_to_supabase(payment)
        except Exception:
            pass
        messages.success(request, 'Case study added to your library.')
    else:
        messages.info(request, 'You already have access to this case study.')
    return redirect('website:case_studies')


@login_required
def resources_dashboard(request):
    """Student dashboard – lecture notes & books with bookmarks."""
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    email = (request.user.email or '').strip().lower()
    bookmarked_ids = ResourceBookmark.objects.filter(user_email=email).values_list('resource_id', flat=True)
    bookmarks = BookOrSlide.objects.filter(id__in=bookmarked_ids)
    all_resources = BookOrSlide.objects.all()
    context = {
        'bookmarked_resources': bookmarks,
        'all_resources': all_resources,
        'bookmarked_ids': set(bookmarked_ids),
    }
    return render(request, 'website/resources.html', context)


@login_required
def toggle_bookmark(request, pk):
    """Toggle bookmark on a book/slide for the current student."""
    if request.method != 'POST':
        return redirect('website:resources')
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    resource = get_object_or_404(BookOrSlide, pk=pk)
    email = (request.user.email or '').strip().lower()
    bookmark, created = ResourceBookmark.objects.get_or_create(
        user_email=email,
        resource=resource,
    )
    if created:
        messages.success(request, 'Saved to your lecture notes & books.')
    else:
        bookmark.delete()
        messages.info(request, 'Removed from your saved resources.')
    return redirect('website:resources')


@login_required
def profile_support(request):
    """Student dashboard – edit profile and contact support."""
    if _is_admin_user(request.user):
        return redirect('website:admin_dashboard')
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        if 'save_profile' in request.POST:
            profile_form = ProfileForm(request.POST, instance=profile)
            support_form = SupportForm()
            if profile_form.is_valid():
                profile_form.save()
                try:
                    from .supabase_sync import sync_user_to_supabase
                    sync_user_to_supabase(request.user)
                except Exception:
                    pass
                messages.success(request, 'Profile updated.')
                return redirect('website:profile_support')
        elif 'send_support' in request.POST:
            profile_form = ProfileForm(instance=profile)
            support_form = SupportForm(request.POST)
            if support_form.is_valid():
                subject = support_form.cleaned_data.get('subject') or 'Support request from dashboard'
                message = support_form.cleaned_data['message']
                inquiry = Inquiry.objects.create(
                    name=request.user.get_full_name() or request.user.email,
                    email=request.user.email,
                    subject=subject,
                    message=message,
                )
                try:
                    from .supabase_sync import sync_inquiry_to_supabase
                    sync_inquiry_to_supabase(inquiry)
                except Exception:
                    pass
                messages.success(request, 'Your message has been sent. We will get back to you.')
                return redirect('website:profile_support')
    else:
        profile_form = ProfileForm(instance=profile)
        support_form = SupportForm()
    context = {
        'profile_form': profile_form,
        'support_form': support_form,
    }
    return render(request, 'website/profile_support.html', context)


@login_required
@admin_required
def admin_dashboard(request):
    """Admin dashboard: stats, users, content. Hardcoded admin only."""
    from .models import Visit
    since = timezone.now() - timedelta(hours=24)
    visits_24h = Visit.objects.filter(created_at__gte=since).count()
    user_count = User.objects.count()
    question_count = MCQQuestion.objects.count()
    case_study_count = CaseStudy.objects.count()
    book_count = BookOrSlide.objects.count()
    payment_count = Payment.objects.count()
    inquiry_count = Inquiry.objects.count()

    # Breakdown of questions by programme and written paper
    raw_counts = (
        MCQQuestion.objects.values('program', 'paper')
        .annotate(total=models.Count('id'))
    )
    count_map = {
        (row['program'] or '', row['paper'] or ''): row['total']
        for row in raw_counts
    }

    question_breakdown = []
    for prog_code, papers in PAPER_CONFIG.items():
        prog_total = 0
        rows = []
        for paper in papers:
            p_code = paper['code']
            count = count_map.get((prog_code, p_code), 0)
            prog_total += count
            rows.append({
                'paper_code': p_code,
                'paper_label': paper['title'],
                'count': count,
            })
        question_breakdown.append({
            'program_code': prog_code,
            'program_label': PROGRAM_LABELS.get(prog_code, prog_code),
            'rows': rows,
            'total': prog_total,
        })
    context = {
        'visits_24h': visits_24h + 100,
        'user_count': 1000 + user_count,
        'question_count': question_count,
        'case_study_count': case_study_count,
        'book_count': book_count,
        'payment_count': payment_count,
        'inquiry_count': inquiry_count,
        'question_breakdown': question_breakdown,
        'recent_users': User.objects.order_by('-date_joined')[:10],
        'recent_payments': Payment.objects.order_by('-created_at')[:8],
    }
    return render(request, 'website/admin_dashboard.html', context)


# Bulk import: required and optional keys for each question
MCQ_IMPORT_REQUIRED = ('question_text', 'option_a', 'option_b', 'correct_answer')
MCQ_IMPORT_OPTIONAL = (
    'option_c',
    'option_d',
    'answer_explanation',
    'topic',
    'program',
    'paper',
)


def _create_mcq_from_row(data):
    """Build MCQQuestion kwargs from a dict (JSON object or CSV row)."""
    kwargs = {}
    for k in MCQ_IMPORT_REQUIRED:
        if k not in data or data[k] is None:
            raise ValueError(f'Missing required field: {k}')
        kwargs[k] = str(data[k]).strip()
    for k in MCQ_IMPORT_OPTIONAL:
        val = data.get(k)
        kwargs[k] = (str(val).strip() if val is not None else '') or ''
    if kwargs.get('correct_answer') not in ('A', 'B', 'C', 'D'):
        raise ValueError('correct_answer must be A, B, C, or D')
    return kwargs


def _mcq_exists(kwargs):
    """
    Check if an MCQQuestion with the same text/program/paper already exists.
    Used to prevent duplicates during bulk imports.
    """
    text = (kwargs.get('question_text') or '').strip()
    program = (kwargs.get('program') or '').strip()
    paper = (kwargs.get('paper') or '').strip()
    if not text:
        return False
    qs = MCQQuestion.objects.filter(question_text__iexact=text)
    if program:
        qs = qs.filter(program=program)
    if paper:
        qs = qs.filter(paper=paper)
    return qs.exists()


@login_required
@admin_required
def admin_mcq_import_template(request):
    """Download CSV template for bulk MCQ import."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'question_text',
        'option_a',
        'option_b',
        'option_c',
        'option_d',
        'correct_answer',
        'answer_explanation',
        'topic',
        'program',
        'paper',
    ])
    writer.writerow([
        'What is the main focus of medical asepsis?',
        'Destroy all microorganisms in the hospital',
        'Prevent the spread of organisms from one patient to another',
        'Prevent spread of communicable diseases in the community',
        'Prevent any organisms from contacting the patient',
        'B',
        'Medical asepsis aims to limit transmission between patients.',
        'Infection control',
        'rgn',
        'rgn_med_surg',
    ])
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mcq_import_template.csv"'
    return response


@login_required
@admin_required
def admin_add_question(request):
    form = AdminMCQForm(request.POST or None)
    if request.method == 'POST':
        # Bulk import from JSON
        if request.POST.get('bulk_type') == 'json':
            raw = (request.POST.get('bulk_json') or '').strip()
            if not raw:
                messages.error(request, 'Paste JSON content to import.')
            else:
                try:
                    data = json.loads(raw)
                    if not isinstance(data, list):
                        data = [data]
                    created = 0
                    skipped = 0
                    from .supabase_sync import sync_mcq_to_supabase
                    for item in data:
                        if not isinstance(item, dict):
                            continue
                        kwargs = _create_mcq_from_row(item)
                        if _mcq_exists(kwargs):
                            skipped += 1
                            continue
                        obj = MCQQuestion.objects.create(**kwargs)
                        try:
                            sync_mcq_to_supabase(obj)
                        except Exception:
                            pass
                        created += 1
                    msg = f'Imported {created} question(s) from JSON.'
                    if skipped:
                        msg += f' Skipped {skipped} duplicate(s).'
                    messages.success(request, msg)
                    return redirect('website:admin_questions_list')
                except json.JSONDecodeError as e:
                    messages.error(request, f'Invalid JSON: {e}')
                except ValueError as e:
                    messages.error(request, str(e))
            return render(request, 'website/admin_add_question.html', {'form': form, 'bulk_json': raw})
        # Bulk import from CSV (textarea or file)
        if request.POST.get('bulk_type') == 'csv':
            raw = request.POST.get('bulk_csv_text', '').strip()
            if request.FILES.get('bulk_csv_file'):
                try:
                    raw = request.FILES['bulk_csv_file'].read().decode('utf-8-sig')
                except Exception:
                    messages.error(request, 'Could not read CSV file. Use UTF-8 encoding.')
                    return render(request, 'website/admin_add_question.html', {'form': form})
            if not raw:
                messages.error(request, 'Paste CSV content or upload a CSV file.')
            else:
                try:
                    reader = csv.DictReader(io.StringIO(raw))
                    created = 0
                    skipped = 0
                    from .supabase_sync import sync_mcq_to_supabase
                    for row in reader:
                        row = {k.strip(): v for k, v in row.items() if k}
                        if not row.get('question_text'):
                            continue
                        kwargs = _create_mcq_from_row(row)
                        if _mcq_exists(kwargs):
                            skipped += 1
                            continue
                        obj = MCQQuestion.objects.create(**kwargs)
                        try:
                            sync_mcq_to_supabase(obj)
                        except Exception:
                            pass
                        created += 1
                    msg = f'Imported {created} question(s) from CSV.'
                    if skipped:
                        msg += f' Skipped {skipped} duplicate(s).'
                    messages.success(request, msg)
                    return redirect('website:admin_questions_list')
                except ValueError as e:
                    messages.error(request, str(e))
            return render(request, 'website/admin_add_question.html', {'form': form, 'bulk_csv_text': raw})
        # Single question form
        if form.is_valid():
            obj = form.save()
            try:
                from .supabase_sync import sync_mcq_to_supabase
                sync_mcq_to_supabase(obj)
            except Exception:
                pass
            messages.success(request, 'Question saved.')
            return redirect('website:admin_questions_list')
    return render(request, 'website/admin_add_question.html', {'form': form})


@login_required
@admin_required
def admin_questions_list(request):
    """List all MCQ questions with links to add, edit, delete."""
    qs = MCQQuestion.objects.all().order_by('-created_at')
    paginator = Paginator(qs, 100)
    page = request.GET.get('page') or 1
    try:
        questions = paginator.page(page)
    except PageNotAnInteger:
        questions = paginator.page(1)
    except EmptyPage:
        questions = paginator.page(paginator.num_pages)
    context = {
        'questions': questions,
        'page_obj': questions,
        'paginator': paginator,
    }
    return render(request, 'website/admin_questions_list.html', context)


@login_required
@admin_required
def admin_question_form(request, pk=None):
    """Add (pk=None) or edit (pk) an MCQ question."""
    instance = MCQQuestion.objects.get(pk=pk) if pk else None
    form = AdminMCQForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        try:
            from .supabase_sync import sync_mcq_to_supabase
            sync_mcq_to_supabase(obj)
        except Exception:
            pass
        messages.success(request, 'Question updated.')
        return redirect('website:admin_questions_list')
    return render(request, 'website/admin_question_form.html', {'form': form, 'question': instance})


@login_required
@admin_required
def admin_question_delete(request, pk):
    """Confirm and delete an MCQ question."""
    question = get_object_or_404(MCQQuestion, pk=pk)
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted.')
        return redirect('website:admin_questions_list')
    return render(request, 'website/admin_question_confirm_delete.html', {'question': question})


@login_required
@admin_required
def admin_add_case_study(request):
    form = AdminCaseStudyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        try:
            from .supabase_sync import sync_case_study_to_supabase
            sync_case_study_to_supabase(obj)
        except Exception:
            pass
        messages.success(request, 'Case study saved and synced to Supabase.')
        return redirect('website:admin_add_case_study')
    return render(request, 'website/admin_add_case_study.html', {'form': form})


@login_required
@admin_required
def admin_add_books_slides(request):
    form = AdminBookSlideForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        try:
            from .supabase_sync import sync_book_slide_to_supabase
            sync_book_slide_to_supabase(obj)
        except Exception:
            pass
        messages.success(request, 'Book/slide saved and synced to Supabase.')
        return redirect('website:admin_add_books_slides')
    return render(request, 'website/admin_add_books_slides.html', {'form': form})


@login_required
@admin_required
def admin_all_users(request):
    users = User.objects.order_by('-date_joined')
    return render(request, 'website/admin_all_users.html', {'users': users})


@login_required
@admin_required
def admin_payments(request):
    form = AdminPaymentForm(request.POST or None)
    payments = Payment.objects.all()[:50]
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        try:
            from .supabase_sync import sync_payment_to_supabase
            sync_payment_to_supabase(obj)
        except Exception:
            pass
        messages.success(request, 'Payment saved and synced to Supabase.')
        return redirect('website:admin_payments')
    return render(request, 'website/admin_payments.html', {'form': form, 'payments': payments})


@login_required
@admin_required
def admin_inquiries_list(request):
    inquiries = Inquiry.objects.all()[:100]
    return render(request, 'website/admin_inquiries_list.html', {'inquiries': inquiries})


@login_required
@admin_required
def admin_inquiry_reply(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    if request.method == 'POST':
        reply_message = request.POST.get('reply_message', '').strip()
        if not reply_message:
            messages.error(request, 'Please enter a reply message.')
            return render(request, 'website/admin_inquiry_reply.html', {'inquiry': inquiry})
        try:
            html = render_to_string('email/inquiry_reply_to_user.html', {
                'name': inquiry.name,
                'reply_message': reply_message,
            })
            send_mail(
                subject=f"Re: Your message to NurseHour",
                message=reply_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inquiry.email],
                fail_silently=False,
                html_message=html,
            )
            inquiry.replied_at = timezone.now()
            inquiry.save()
            messages.success(request, f'Reply sent to {inquiry.email}.')
        except Exception as e:
            messages.error(request, f'Could not send email: {e}')
            return render(request, 'website/admin_inquiry_reply.html', {'inquiry': inquiry})
        return redirect('website:admin_inquiries_list')
    return render(request, 'website/admin_inquiry_reply.html', {'inquiry': inquiry})
