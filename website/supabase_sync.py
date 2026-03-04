"""Sync Django data to Supabase (app_users, mcq_questions, case_studies, books_slides, payments).

By default, syncing is DISABLED. Django already uses its configured DATABASE_URL
(e.g. Supabase Postgres) as the primary database, so all reads/writes go there
directly. These helpers are now opt‑in only to avoid duplicate writes.
"""
import json
import urllib.request
from django.conf import settings

SYNC_ENABLED = getattr(settings, 'SUPABASE_SYNC_ENABLED', False)


def _supabase_post(table, data):
    if not SYNC_ENABLED:
        return
    url = getattr(settings, 'SUPABASE_URL', None)
    key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or getattr(settings, 'SUPABASE_KEY', None)
    if not url or not key:
        return
    api = url.rstrip('/') + '/rest/v1/' + table
    req = urllib.request.Request(
        api,
        data=json.dumps(data).encode('utf-8'),
        headers={
            'apikey': key,
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal',
        },
        method='POST',
    )
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass


def sync_user_to_supabase(user):
    """Insert or update user in Supabase public.app_users. Fails silently if not configured."""
    if not SYNC_ENABLED:
        return
    url = getattr(settings, 'SUPABASE_URL', None)
    key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or getattr(settings, 'SUPABASE_KEY', None)
    if not url or not key:
        return
    api = url.rstrip('/') + '/rest/v1/app_users'
    program = None
    try:
        profile = getattr(user, 'profile', None)
        if profile and getattr(profile, 'program', ''):
            program = profile.program
    except Exception:
        program = None
    data = json.dumps({
        'email': user.email,
        'full_name': (user.get_full_name() or user.email).strip() or None,
        'program': program,
    }).encode('utf-8')
    req = urllib.request.Request(
        api,
        data=data,
        headers={
            'apikey': key,
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates',
        },
        method='POST',
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def sync_mcq_to_supabase(mcq):
    if not SYNC_ENABLED:
        return
    _supabase_post('mcq_questions', {
        'question_text': mcq.question_text,
        'option_a': mcq.option_a,
        'option_b': mcq.option_b,
        'option_c': mcq.option_c or None,
        'option_d': mcq.option_d or None,
        'correct_answer': mcq.correct_answer,
        'answer_explanation': mcq.answer_explanation or None,
        'topic': mcq.topic or None,
        'program': mcq.program or None,
        'paper': mcq.paper or None,
    })


def sync_case_study_to_supabase(case):
    if not SYNC_ENABLED:
        return
    _supabase_post('case_studies', {
        'title': case.title,
        'scenario': case.scenario or None,
        'content': case.content or None,
        'file_url': case.file_url or None,
    })


def sync_book_slide_to_supabase(book):
    if not SYNC_ENABLED:
        return
    _supabase_post('books_slides', {
        'title': book.title,
        'description': book.description or None,
        'file_url': book.file_url or None,
        'kind': book.kind,
    })


def sync_payment_to_supabase(payment):
    if not SYNC_ENABLED:
        return
    _supabase_post('payments', {
        'user_email': payment.user_email or None,
        'amount': str(payment.amount),
        'status': payment.status,
        'description': payment.description or None,
    })


def sync_inquiry_to_supabase(inquiry):
    if not SYNC_ENABLED:
        return
    _supabase_post('inquiries', {
        'name': inquiry.name,
        'email': inquiry.email,
        'subject': inquiry.subject or '',
        'message': inquiry.message,
        'replied_at': inquiry.replied_at.isoformat() if inquiry.replied_at else None,
    })


def sync_practice_session_to_supabase(session, supabase_id=None):
    """Store a practice session summary in Supabase public.practice_sessions."""
    if not SYNC_ENABLED:
        return
    user_email = getattr(session.user, 'email', None)
    payload = {
        'django_session_id': session.id,
        'user_email': user_email,
        'program': getattr(session, 'program', None) or None,
        'paper': getattr(session, 'paper', None) or None,
        'timed': bool(getattr(session, 'timed', False)),
        'total_questions': session.total_questions,
        'correct_count': session.correct_count,
        'started_at': session.started_at.isoformat() if session.started_at else None,
        'finished_at': session.finished_at.isoformat() if session.finished_at else None,
    }
    _supabase_post('practice_sessions', payload)


def sync_practice_answer_to_supabase(answer, practice_session_supabase_id=None):
    """Store a single practice answer row in Supabase public.practice_answers."""
    if not SYNC_ENABLED:
        return
    q = answer.question
    session = answer.session
    user_email = getattr(answer.user, 'email', None)
    payload = {
        'practice_session_id': practice_session_supabase_id,
        'django_session_id': session.id,
        'user_email': user_email,
        'question_text': q.question_text,
        'chosen_answer': answer.chosen_answer,
        'correct_answer': q.correct_answer,
        'is_correct': answer.is_correct,
        'program': getattr(session, 'program', None) or None,
        'paper': getattr(session, 'paper', None) or None,
        'topic': q.topic or None,
        'answered_at': answer.answered_at.isoformat() if answer.answered_at else None,
    }
    _supabase_post('practice_answers', payload)
