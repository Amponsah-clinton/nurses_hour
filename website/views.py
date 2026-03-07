import csv
import json
import io

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
import base64
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


# Minimal 1x1 transparent PNG so favicon requests don't 404 (Vercel/browser)
_FAVICON_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
)


def favicon_view(request):
    return HttpResponse(_FAVICON_PNG, content_type='image/png')


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
    Inquiry.objects.create(name=name, email=email, subject=subject, message=message)
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
        email = form.cleaned_data['email'].lower().strip()
        name = (form.cleaned_data.get('name') or '').strip()
        password = form.cleaned_data['password']
        phone = (form.cleaned_data.get('phone') or '').strip()
        program = (form.cleaned_data.get('program') or '').strip()
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name or email,
        )
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'phone': phone, 'program': program})
        profile.phone = phone or profile.phone
        profile.program = program or profile.program
        profile.save(update_fields=['phone', 'program'])
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
            email_or_phone = (form.cleaned_data['email_or_phone'] or '').strip()
            password = form.cleaned_data['password']
            email = email_or_phone

            # Phone → look up email from Django UserProfile
            if '@' not in email_or_phone:
                profile = UserProfile.objects.filter(phone=email_or_phone).select_related('user').first()
                if not profile:
                    form.add_error(None, 'No account found with this phone number.')
                    return render(request, 'website/login.html', {'form': form})
                email = profile.user.email

            # Ensure admin user exists (Django User) for admin email
            admin_email = getattr(settings, 'ADMIN_EMAIL', None)
            admin_password = getattr(settings, 'ADMIN_INITIAL_PASSWORD', None)
            if admin_email and email.strip().lower() == admin_email.strip().lower() and admin_password:
                User.objects.get_or_create(
                    email=admin_email,
                    defaults={
                        'username': admin_email,
                        'first_name': 'Admin',
                    }
                )
                admin_user = User.objects.get(email=admin_email)
                if not admin_user.check_password(admin_password):
                    admin_user.set_password(admin_password)
                    admin_user.save(update_fields=['password'])

            user = authenticate(request, username=email, password=password)
            if not user:
                form.add_error(None, 'Invalid email/phone or password.')
                return render(request, 'website/login.html', {'form': form})
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'Welcome back, {user.get_short_name() or email}!')
            return redirect_to_dashboard(user)
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
        # Fetch questions from Django (SQLite); filter by program/paper
        qs = MCQQuestion.objects.all().order_by('-created_at')
        if program:
            qs = qs.filter(program=program)
        if paper:
            qs = qs.filter(paper=paper)
        # Exclude already-answered question IDs (Django FK)
        answered_ids = set(
            PracticeAnswer.objects.filter(user=request.user)
            .exclude(question__isnull=True)
            .values_list('question_id', flat=True)
        )
        candidate = list(qs.exclude(pk__in=answered_ids).values_list('pk', flat=True))
        import random
        random.shuffle(candidate)
        total_available = len(candidate)
        if total_available == 0:
            candidate = list(qs.values_list('pk', flat=True))
            random.shuffle(candidate)
            total_available = len(candidate)
            if total_available == 0:
                messages.info(request, 'No questions are available yet for this paper. Please check back soon.')
                return redirect('website:practice')
            messages.info(request, 'You have answered all existing questions for this paper. We will now repeat questions for extra practice.')
        take = min(num_questions, total_available)
        question_ids = [int(candidate[i]) for i in range(take)]
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
    """Show a single question within a practice session (question from Django/SQLite) and record the answer."""
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
    try:
        question_id = int(questions[index - 1])
    except (TypeError, ValueError):
        messages.error(request, 'Question could not be loaded.')
        return redirect('website:practice')
    question = MCQQuestion.objects.filter(pk=question_id).first()
    if not question:
        messages.error(request, 'Question could not be loaded.')
        return redirect('website:practice')
    if request.method == 'POST':
        chosen = (request.POST.get('answer') or '').strip().upper()
        if chosen not in dict(MCQQuestion.CORRECT_CHOICES):
            messages.error(request, 'Please select an answer before continuing.')
            return redirect('website:practice_session_question', session_id=session.id, index=index)
        correct_ans = (question.correct_answer or 'A').strip().upper()[:1]
        is_correct = (chosen == correct_ans)
        PracticeAnswer.objects.update_or_create(
            session=session,
            order_index=index,
            defaults={
                'user': request.user,
                'question': question,
                'question_supabase_id': '',
                'question_text': question.question_text or '',
                'correct_answer': correct_ans,
                'answer_explanation': question.answer_explanation or '',
                'chosen_answer': chosen,
                'is_correct': is_correct,
            },
        )
        correct_count = PracticeAnswer.objects.filter(session=session, is_correct=True).count()
        session.correct_count = correct_count
        if index == total and session.finished_at is None:
            session.finished_at = timezone.now()
        session.save(update_fields=['correct_count', 'finished_at'])
        if index >= total:
            return redirect('website:practice_review', session_id=session.id)
        return redirect('website:practice_session_question', session_id=session.id, index=index + 1)
    progress_pct = int((index / float(total)) * 100)
    answered_indices = set(
        PracticeAnswer.objects.filter(session=session).values_list('order_index', flat=True)
    )
    current_answer = None
    existing = PracticeAnswer.objects.filter(session=session, order_index=index).first()
    if existing:
        current_answer = existing.chosen_answer or ''
    question_numbers = list(range(1, total + 1))
    context = {
        'session': session,
        'question': question,
        'index': index,
        'total': total,
        'progress_pct': progress_pct,
        'timed': session.timed,
        'seconds_per_question': 50,
        'answered_indices': answered_indices,
        'chosen_answer': current_answer,
        'question_numbers': question_numbers,
    }
    return render(request, 'website/practice_run.html', context)


@login_required
def practice_review(request, session_id):
    """Review all questions and answers for a completed practice session (Supabase or legacy)."""
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


def public_case_studies(request):
    """Public catalogue – anyone can browse; login required to purchase."""
    all_cases = CaseStudy.objects.all()
    owned_ids = set()
    if request.user.is_authenticated:
        email = (request.user.email or '').strip().lower()
        owned_ids = set(CaseStudyAccess.objects.filter(user_email=email).values_list('case_study_id', flat=True))
    return render(request, 'website/public_case_studies.html', {
        'all_case_studies': all_cases,
        'owned_ids': owned_ids,
        'case_study_price': 2,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    })


@login_required
def initiate_case_study_payment(request, pk):
    """Start a Paystack payment of GHS 2 for a case study."""
    import requests as http_req
    if request.method != 'POST':
        return redirect('website:public_case_studies')
    case = get_object_or_404(CaseStudy, pk=pk)
    email = (request.user.email or '').strip().lower()
    # Already owned – skip payment
    if CaseStudyAccess.objects.filter(user_email=email, case_study=case).exists():
        messages.info(request, 'You already have access to this case study.')
        return redirect('website:public_case_studies')
    callback_url = request.build_absolute_uri(reverse('website:verify_case_study_payment'))
    payload = {
        'email': email,
        'amount': 200,          # GHS 2 = 200 pesewas
        'currency': 'GHS',
        'callback_url': callback_url,
        'metadata': {
            'case_study_id': pk,
            'case_study_title': case.title,
            'user_email': email,
        },
    }
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    try:
        resp = http_req.post(
            'https://api.paystack.co/transaction/initialize',
            json=payload, headers=headers, timeout=15,
        )
        data = resp.json()
        auth_url = data.get('data', {}).get('authorization_url')
        if data.get('status') and auth_url:
            return redirect(auth_url)
        messages.error(request, f'Payment could not be started: {data.get("message", "unknown error")}')
    except Exception:
        messages.error(request, 'Payment service unavailable. Please try again shortly.')
    return redirect('website:public_case_studies')


@login_required
def verify_case_study_payment(request):
    """Paystack callback – verify payment and grant case study access."""
    import requests as http_req
    reference = request.GET.get('trxref') or request.GET.get('reference')
    if not reference:
        messages.error(request, 'Payment reference missing.')
        return redirect('website:public_case_studies')
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    try:
        resp = http_req.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers, timeout=15,
        )
        data = resp.json()
        tx = data.get('data', {})
        if data.get('status') and tx.get('status') == 'success':
            meta = tx.get('metadata', {})
            case_study_id = meta.get('case_study_id')
            email = (request.user.email or '').strip().lower()
            if case_study_id:
                case = get_object_or_404(CaseStudy, pk=case_study_id)
                access, created = CaseStudyAccess.objects.get_or_create(
                    user_email=email, case_study=case,
                )
                if created:
                    amount_paid = tx.get('amount', 200) / 100
                    payment = Payment.objects.create(
                        user_email=email,
                        amount=amount_paid,
                        status='completed',
                        description=f'Case study: {case.title} (ref: {reference})',
                    )
                    access.payment = payment
                    access.save(update_fields=['payment'])
                    messages.success(request, f'Payment successful! "{case.title}" is now in your library.')
                else:
                    messages.info(request, 'You already have access to this case study.')
            else:
                messages.warning(request, 'Payment verified but no case study was linked.')
        else:
            messages.error(request, 'Payment was not successful. Please try again.')
    except Exception:
        messages.error(request, 'Could not verify payment. Please contact support.')
    return redirect('website:public_case_studies')


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
                messages.success(request, 'Profile updated.')
                return redirect('website:profile_support')
        elif 'send_support' in request.POST:
            profile_form = ProfileForm(instance=profile)
            support_form = SupportForm(request.POST)
            if support_form.is_valid():
                subject = support_form.cleaned_data.get('subject') or 'Support request from dashboard'
                message = support_form.cleaned_data['message']
                Inquiry.objects.create(
                    name=request.user.get_full_name() or request.user.email,
                    email=request.user.email,
                    subject=subject,
                    message=message,
                )
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
    """Admin dashboard: stats and content — all from Django/SQLite."""
    from .models import Visit
    try:
        since = timezone.now() - timedelta(hours=24)
        visits_24h = Visit.objects.filter(created_at__gte=since).count()
    except Exception:
        visits_24h = 0

    question_count = MCQQuestion.objects.count()
    case_study_count = CaseStudy.objects.count()
    book_count = BookOrSlide.objects.count()
    payment_count = Payment.objects.count()
    inquiry_count = Inquiry.objects.count()
    user_count = User.objects.count()

    # Question breakdown by programme & paper
    from collections import Counter
    count_map = Counter(
        (q.program or '', q.paper or '')
        for q in MCQQuestion.objects.all()
    )
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

    recent_users_qs = User.objects.select_related('profile').order_by('-date_joined')[:10]
    recent_users = [
        {
            'email': u.email or '—',
            'full_name': u.get_full_name() or u.email or '—',
            'created_at': u.date_joined,
        }
        for u in recent_users_qs
    ]
    recent_payments = list(Payment.objects.order_by('-created_at')[:8])

    context = {
        'visits_24h': visits_24h,
        'user_count': user_count,
        'question_count': question_count,
        'case_study_count': case_study_count,
        'book_count': book_count,
        'payment_count': payment_count,
        'inquiry_count': inquiry_count,
        'question_breakdown': question_breakdown,
        'recent_users': recent_users,
        'recent_payments': recent_payments,
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


def _mcq_payload_from_row(row):
    """Build MCQQuestion kwargs from a row (JSON object or CSV row)."""
    return {
        'question_text': (row.get('question_text') or '').strip(),
        'option_a': (row.get('option_a') or '').strip(),
        'option_b': (row.get('option_b') or '').strip(),
        'option_c': (row.get('option_c') or '').strip() or '',
        'option_d': (row.get('option_d') or '').strip() or '',
        'correct_answer': (row.get('correct_answer') or 'A').strip().upper()[:1] or 'A',
        'answer_explanation': (row.get('answer_explanation') or '').strip() or '',
        'topic': (row.get('topic') or '').strip() or '',
        'program': (row.get('program') or '').strip() or '',
        'paper': (row.get('paper') or '').strip() or '',
    }


@login_required
@admin_required
def admin_add_question(request):
    """Add questions to Django/SQLite (single or bulk JSON/CSV)."""
    form = AdminMCQForm(request.POST or None)
    if request.method == 'POST':
        if request.POST.get('bulk_type') == 'json':
            raw = (request.POST.get('bulk_json') or '').strip()
            if not raw:
                messages.error(request, 'Paste JSON content to import.')
            else:
                try:
                    data = json.loads(raw)
                    if not isinstance(data, list):
                        data = [data]
                    created = failed = 0
                    for item in data:
                        if not isinstance(item, dict) or not (item.get('question_text') or '').strip():
                            continue
                        payload = _mcq_payload_from_row(item)
                        if payload.get('correct_answer') not in ('A', 'B', 'C', 'D'):
                            failed += 1
                            continue
                        try:
                            MCQQuestion.objects.create(**payload)
                            created += 1
                        except Exception:
                            failed += 1
                    msg = f'Imported {created} question(s).'
                    if failed:
                        msg += f' {failed} failed.'
                    messages.success(request, msg)
                    return redirect('website:admin_questions_list')
                except json.JSONDecodeError as e:
                    messages.error(request, f'Invalid JSON: {e}')
            return render(request, 'website/admin_add_question.html', {'form': form, 'bulk_json': raw})
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
                    created = failed = 0
                    for row in reader:
                        row = {k.strip(): v for k, v in row.items() if k}
                        if not (row.get('question_text') or '').strip():
                            continue
                        payload = _mcq_payload_from_row(row)
                        if payload.get('correct_answer') not in ('A', 'B', 'C', 'D'):
                            failed += 1
                            continue
                        try:
                            MCQQuestion.objects.create(**payload)
                            created += 1
                        except Exception:
                            failed += 1
                    msg = f'Imported {created} question(s).'
                    if failed:
                        msg += f' {failed} failed.'
                    messages.success(request, msg)
                    return redirect('website:admin_questions_list')
                except ValueError as e:
                    messages.error(request, str(e))
            return render(request, 'website/admin_add_question.html', {'form': form, 'bulk_csv_text': raw})
        if form.is_valid():
            form.save()
            messages.success(request, 'Question saved successfully.')
            return redirect('website:admin_questions_list')
    return render(request, 'website/admin_add_question.html', {'form': form})


@login_required
@admin_required
def admin_questions_list(request):
    """List all MCQ questions from Django/SQLite with links to add, edit, delete."""
    questions_list = MCQQuestion.objects.all().order_by('-created_at')
    paginator = Paginator(questions_list, 100)
    page = request.GET.get('page') or 1
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    context = {
        'questions': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
    }
    return render(request, 'website/admin_questions_list.html', context)


@login_required
@admin_required
def admin_question_form(request, pk=None):
    """Add (pk=None) or edit (pk=Django id) an MCQ question — Django/SQLite only."""
    question = get_object_or_404(MCQQuestion, pk=pk) if pk else None
    form = AdminMCQForm(request.POST or None, instance=question)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Question saved successfully.')
        return redirect('website:admin_questions_list')
    return render(request, 'website/admin_question_form.html', {'form': form, 'question': question})


@login_required
@admin_required
def admin_question_delete(request, pk):
    """Confirm and delete an MCQ question from Django/SQLite."""
    question = get_object_or_404(MCQQuestion, pk=pk)
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Question deleted.')
        return redirect('website:admin_questions_list')
    return render(request, 'website/admin_question_confirm_delete.html', {'question': question})


@login_required
@admin_required
def admin_add_case_study(request):
    from django.core.files.storage import default_storage
    form = AdminCaseStudyForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        if request.FILES.get('upload_file'):
            f = request.FILES['upload_file']
            path = default_storage.save(f'case_studies/{f.name}', f)
            obj.file_url = request.build_absolute_uri(settings.MEDIA_URL + path)
            obj.save(update_fields=['file_url'])
        messages.success(request, 'Case study saved successfully.')
        return redirect('website:admin_add_case_study')
    return render(request, 'website/admin_add_case_study.html', {'form': form})


@login_required
@admin_required
def admin_add_books_slides(request):
    from django.core.files.storage import default_storage
    form = AdminBookSlideForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        if request.FILES.get('upload_file'):
            f = request.FILES['upload_file']
            path = default_storage.save(f'books_slides/{f.name}', f)
            obj.file_url = request.build_absolute_uri(settings.MEDIA_URL + path)
            obj.save(update_fields=['file_url'])
        messages.success(request, 'Book/slide saved successfully.')
        return redirect('website:admin_add_books_slides')
    return render(request, 'website/admin_add_books_slides.html', {'form': form})


@login_required
@admin_required
def admin_content_supabase(request):
    """Admin page: Case studies and Books & slides from Django/SQLite, in tabs."""
    case_studies = CaseStudy.objects.all().order_by('-created_at')
    books_slides = BookOrSlide.objects.all().order_by('-created_at')
    return render(request, 'website/admin_content_supabase.html', {
        'case_studies': case_studies,
        'case_studies_error': None,
        'books_slides': books_slides,
        'books_slides_error': None,
    })


@login_required
@admin_required
def admin_all_users(request):
    users_qs = User.objects.select_related('profile').order_by('-date_joined')
    users = [
        {
            'email': u.email or '—',
            'full_name': u.get_full_name() or u.email or '—',
            'program': getattr(getattr(u, 'profile', None), 'program', '') or '—',
            'created_at': u.date_joined,
        }
        for u in users_qs
    ]
    return render(request, 'website/admin_all_users.html', {'users': users})


@login_required
@admin_required
def admin_payments(request):
    """List all payments from Django/SQLite."""
    payments = Payment.objects.all().order_by('-created_at')[:100]
    return render(request, 'website/admin_payments.html', {'payments': payments})


def _parse_iso_date(iso_str):
    """Parse Supabase ISO timestamp for display. Returns None or datetime."""
    if not iso_str:
        return None
    try:
        s = str(iso_str).replace('Z', '+00:00')
        return timezone.datetime.fromisoformat(s)
    except Exception:
        return None


@login_required
@admin_required
def admin_inquiries_list(request):
    """Display contact form submissions from Django/SQLite."""
    inquiries = Inquiry.objects.all().order_by('-created_at')
    return render(request, 'website/admin_inquiries_list.html', {'inquiries': inquiries})


@login_required
@admin_required
def admin_inquiry_reply(request, pk):
    """Reply to an inquiry by Django pk; send email and set replied_at."""
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
