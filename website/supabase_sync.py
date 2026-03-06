"""
Direct Supabase REST API helpers for NurseHour.

Every public function saves a row directly to Supabase and returns (True, None)
on success, or (False, error_message) on failure so the caller can show real
feedback instead of silently ignoring errors.
"""
import json
import urllib.request
import urllib.error
import uuid
from django.conf import settings


# ── Low-level helpers ────────────────────────────────────────────────────────

def _cfg():
    """Return (url, service_key) from settings. Raises ValueError if not configured."""
    url = getattr(settings, 'SUPABASE_URL', None)
    key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or getattr(settings, 'SUPABASE_KEY', None)
    if not url or not key:
        raise ValueError('SUPABASE_URL / SUPABASE_SERVICE_KEY are not configured in settings.')
    return url.rstrip('/'), key


def _post(table, payload, prefer='resolution=merge-duplicates'):
    """
    POST a single row to Supabase REST API.
    Returns (True, None) on success, (False, error_str) on failure.
    """
    try:
        url, key = _cfg()
    except ValueError as e:
        return False, str(e)

    api = '{}/rest/v1/{}'.format(url, table)
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        api,
        data=body,
        headers={
            'apikey': key,
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json',
            'Prefer': prefer,
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
        if status in (200, 201):
            return True, None
        return False, 'Supabase returned HTTP {}'.format(status)
    except urllib.error.HTTPError as e:
        body_bytes = b''
        try:
            body_bytes = e.read()
        except Exception:
            pass
        detail = body_bytes.decode('utf-8', errors='replace') or str(e)
        return False, 'HTTP {}: {}'.format(e.code, detail)
    except Exception as e:
        return False, str(e)


def _get(table, order='created_at.desc', filters=None):
    """
    GET rows from Supabase REST API. order e.g. 'created_at.desc' or None.
    filters: optional dict e.g. {'program': 'rgn', 'paper': 'rgn_med_surg'} -> &program=eq.rgn&paper=eq.rgn_med_surg
    Returns (list_of_dicts, None) on success, ([], error_msg) on failure.
    """
    try:
        url, key = _cfg()
    except ValueError as e:
        return [], str(e)
    api = '{}/rest/v1/{}?select=*'.format(url, table)
    if order:
        api = api + '&order=' + order
    if filters:
        for k, v in filters.items():
            if v is not None and v != '':
                api = api + '&{}={}'.format(k, 'eq.' + str(v))
    req = urllib.request.Request(
        api,
        headers={
            'apikey': key,
            'Authorization': 'Bearer ' + key,
            'Accept': 'application/json',
        },
        method='GET',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data if isinstance(data, list) else [], None
    except urllib.error.HTTPError as e:
        body_bytes = b''
        try:
            body_bytes = e.read()
        except Exception:
            pass
        detail = body_bytes.decode('utf-8', errors='replace') or str(e)
        return [], 'HTTP {}: {}'.format(e.code, detail)
    except Exception as e:
        return [], str(e)


def _get_by_id(table, row_id):
    """GET one row by id. Returns (dict or None, error_msg)."""
    rows, err = _get(table, order=None, filters={'id': row_id})
    if err:
        return None, err
    if rows and len(rows) > 0:
        return rows[0], None
    return None, 'Not found'


def fetch_case_studies_from_supabase():
    """Fetch all rows from Supabase public.case_studies. Returns (list, error_msg)."""
    return _get('case_studies', order='created_at.desc')


def fetch_books_slides_from_supabase():
    """Fetch all rows from Supabase public.books_slides. Returns (list, error_msg)."""
    return _get('books_slides', order='created_at.desc')


def fetch_inquiries_from_supabase():
    """Fetch all rows from Supabase public.inquiries. Returns (list, error_msg)."""
    return _get('inquiries', order='created_at.desc')


def fetch_inquiry_by_id_supabase(supabase_id):
    """Fetch one inquiry from Supabase by id. Returns (dict or None, error_msg)."""
    return _get_by_id('inquiries', supabase_id)


def fetch_mcq_questions_from_supabase(order='created_at.desc', program=None, paper=None):
    """Fetch MCQ questions from Supabase. Optional program/paper filter. Returns (list, error_msg)."""
    filters = {}
    if program:
        filters['program'] = program
    if paper:
        filters['paper'] = paper
    return _get('mcq_questions', order=order, filters=filters if filters else None)


def fetch_mcq_question_by_id_supabase(supabase_id):
    """Fetch one MCQ question by Supabase id. Returns (dict or None, error_msg)."""
    return _get_by_id('mcq_questions', supabase_id)


def add_mcq_to_supabase(payload):
    """Insert one MCQ into Supabase. payload: dict with question_text, option_a, option_b, etc. Returns (id, None) or (None, error_msg)."""
    rows, err = _post_return('mcq_questions', payload, return_data=True)
    if err or not rows:
        return None, err or 'No data returned'
    try:
        return rows[0]['id'], None
    except (KeyError, IndexError, TypeError):
        return None, 'Could not read id from response'


def update_mcq_in_supabase(supabase_id, payload):
    """Update an MCQ in Supabase by id. Returns (True, None) or (False, error_msg)."""
    return _patch('mcq_questions', supabase_id, payload)


def delete_mcq_from_supabase(supabase_id):
    """Delete an MCQ in Supabase by id. Returns (True, None) or (False, error_msg)."""
    return _delete('mcq_questions', supabase_id)


def get_app_user_email_by_phone(phone):
    """Get email from app_users by phone (if table has phone column). Returns (email or None, error_msg)."""
    rows, err = _get('app_users', order=None, filters={'phone': str(phone).strip()})
    if err or not rows:
        return None, err or 'Not found'
    return (rows[0].get('email') or None), None


def _delete(table, row_id):
    """
    DELETE a row in Supabase by id (uuid or int).
    Returns (True, None) on success, (False, error_str) on failure.
    """
    try:
        url, key = _cfg()
    except ValueError as e:
        return False, str(e)
    api = '{}/rest/v1/{}?id=eq.{}'.format(url, table, row_id)
    req = urllib.request.Request(
        api,
        headers={
            'apikey': key,
            'Authorization': 'Bearer ' + key,
        },
        method='DELETE',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
        return True, None
    except urllib.error.HTTPError as e:
        return False, 'HTTP {}: {}'.format(e.code, e.reason)
    except Exception as e:
        return False, str(e)


def _post(table, payload, prefer='resolution=merge-duplicates'):
    """
    POST a single row to Supabase REST API.
    Returns (True, None) on success, (False, error_str) on failure.
    """
    return _post_return(table, payload, prefer=prefer, return_data=False)


def _post_return(table, payload, prefer='resolution=merge-duplicates', return_data=True):
    """
    POST a single row; if return_data=True use Prefer: return=representation.
    Returns (True, None) or (data, None) when return_data=True; (False, error_str) on failure.
    When return_data=True, returns (list_with_one_row, None) so caller can get id from row[0]['id'].
    """
    try:
        url, key = _cfg()
    except ValueError as e:
        return (None if return_data else False), str(e)
    api = '{}/rest/v1/{}'.format(url, table)
    body = json.dumps(payload).encode('utf-8')
    headers = {
        'apikey': key,
        'Authorization': 'Bearer ' + key,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation' if return_data else prefer,
    }
    req = urllib.request.Request(api, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if return_data:
                data = json.loads(resp.read().decode('utf-8'))
                return (data if isinstance(data, list) else [data]), None
            return True, None
    except urllib.error.HTTPError as e:
        body_bytes = b''
        try:
            body_bytes = e.read()
        except Exception:
            pass
        detail = body_bytes.decode('utf-8', errors='replace') or str(e)
        return (None if return_data else False), 'HTTP {}: {}'.format(e.code, detail)
    except Exception as e:
        return (None if return_data else False), str(e)


def _patch(table, row_id, payload):
    """
    PATCH a row in Supabase by id (uuid or int).
    Returns (True, None) on success, (False, error_str) on failure.
    """
    try:
        url, key = _cfg()
    except ValueError as e:
        return False, str(e)
    api = '{}/rest/v1/{}?id=eq.{}'.format(url, table, row_id)
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        api,
        data=body,
        headers={
            'apikey': key,
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json',
        },
        method='PATCH',
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
        return True, None
    except urllib.error.HTTPError as e:
        body_bytes = b''
        try:
            body_bytes = e.read()
        except Exception:
            pass
        detail = body_bytes.decode('utf-8', errors='replace') or str(e)
        return False, 'HTTP {}: {}'.format(e.code, detail)
    except Exception as e:
        return False, str(e)


def update_inquiry_replied_at_supabase(supabase_id):
    """Set replied_at to now() for an inquiry row in Supabase. Returns (ok, error_msg)."""
    from datetime import datetime, timezone
    return _patch('inquiries', supabase_id, {
        'replied_at': datetime.now(tz=timezone.utc).isoformat(),
    })


def _storage_upload(bucket, path, data, content_type='application/octet-stream'):
    """
    Upload raw bytes to Supabase Storage. path is the object path inside the bucket (e.g. 'file.pdf').
    Returns (True, public_url) or (False, error_msg).
    """
    try:
        url, key = _cfg()
    except ValueError as e:
        return False, str(e)
    api = '{}/storage/v1/object/{}'.format(url, bucket)
    if path:
        api = api + '/' + path.lstrip('/')
    req = urllib.request.Request(
        api,
        data=data,
        headers={
            'apikey': key,
            'Authorization': 'Bearer ' + key,
            'Content-Type': content_type,
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            pass
        public_url = '{}/storage/v1/object/public/{}/{}'.format(url, bucket, path.lstrip('/'))
        return True, public_url
    except urllib.error.HTTPError as e:
        body_bytes = b''
        try:
            body_bytes = e.read()
        except Exception:
            pass
        detail = body_bytes.decode('utf-8', errors='replace') or str(e)
        return False, 'HTTP {}: {}'.format(e.code, detail)
    except Exception as e:
        return False, str(e)


def upload_case_study_file(file_obj):
    """
    Upload a case study file to the Supabase case-studies bucket.
    file_obj: Django UploadedFile (request.FILES['...']).
    Returns (True, public_url) or (False, error_msg).
    """
    bucket = getattr(settings, 'SUPABASE_STORAGE_BUCKET_CASE_STUDIES', 'case-studies')
    name = (file_obj.name or 'file').replace('\\', '/').split('/')[-1]
    safe = ''.join(c for c in name if c.isalnum() or c in '.-_ ')
    if not safe:
        safe = 'file'
    path = '{}_{}'.format(uuid.uuid4().hex[:12], safe)
    content_type = getattr(file_obj, 'content_type', None) or 'application/octet-stream'
    data = file_obj.read()
    return _storage_upload(bucket, path, data, content_type=content_type)


def upload_book_slide_file(file_obj):
    """
    Upload a book/slide file to the Supabase book-slide bucket.
    file_obj: Django UploadedFile (request.FILES['...']).
    Returns (True, public_url) or (False, error_msg).
    """
    bucket = getattr(settings, 'SUPABASE_STORAGE_BUCKET_BOOKS_SLIDES', 'book-slide')
    name = (file_obj.name or 'file').replace('\\', '/').split('/')[-1]
    safe = ''.join(c for c in name if c.isalnum() or c in '.-_ ')
    if not safe:
        safe = 'file'
    path = '{}_{}'.format(uuid.uuid4().hex[:12], safe)
    content_type = getattr(file_obj, 'content_type', None) or 'application/octet-stream'
    data = file_obj.read()
    return _storage_upload(bucket, path, data, content_type=content_type)


# ── Public save functions ─────────────────────────────────────────────────────

def save_mcq_to_supabase(mcq):
    """Save an MCQQuestion directly to Supabase public.mcq_questions."""
    return _post('mcq_questions', {
        'question_text':     mcq.question_text,
        'option_a':          mcq.option_a,
        'option_b':          mcq.option_b,
        'option_c':          mcq.option_c or None,
        'option_d':          mcq.option_d or None,
        'correct_answer':    mcq.correct_answer,
        'answer_explanation': mcq.answer_explanation or None,
        'topic':             mcq.topic or None,
        'program':           mcq.program or None,
        'paper':             mcq.paper or None,
    })


def save_user_to_supabase(user):
    """Save/upsert a user directly to Supabase public.app_users (email, full_name, program, phone for login-by-phone)."""
    program = None
    phone = None
    try:
        profile = getattr(user, 'profile', None)
        if profile:
            program = getattr(profile, 'program', None) or None
            phone = getattr(profile, 'phone', None) or None
    except Exception:
        pass
    return _post('app_users', {
        'email':     user.email,
        'full_name': (user.get_full_name() or user.email or '').strip() or None,
        'program':   program,
        'phone':     (phone or '').strip() or None,
    })


def save_case_study_to_supabase(case):
    """Save a CaseStudy directly to Supabase public.case_studies."""
    return _post('case_studies', {
        'title':    case.title,
        'scenario': case.scenario or None,
        'content':  case.content or None,
        'file_url': case.file_url or None,
    })


def save_book_slide_to_supabase(book):
    """Save a BookOrSlide directly to Supabase public.books_slides."""
    return _post('books_slides', {
        'title':       book.title,
        'description': book.description or None,
        'file_url':    book.file_url or None,
        'kind':        book.kind,
    })


def save_payment_to_supabase(payment):
    """Save a Payment directly to Supabase public.payments."""
    return _post('payments', {
        'user_email':  payment.user_email or None,
        'amount':      str(payment.amount),
        'status':      payment.status,
        'description': payment.description or None,
    })


def save_inquiry_to_supabase(inquiry):
    """Save an Inquiry directly to Supabase public.inquiries."""
    return _post('inquiries', {
        'name':       inquiry.name,
        'email':      inquiry.email,
        'subject':    inquiry.subject or '',
        'message':    inquiry.message,
        'replied_at': inquiry.replied_at.isoformat() if inquiry.replied_at else None,
    })


def save_practice_session_to_supabase(session):
    """Save or update a PracticeSession in Supabase (upsert on django_session_id)."""
    payload = {
        'django_session_id': session.id,
        'user_email':        getattr(session.user, 'email', None),
        'program':           getattr(session, 'program', None) or None,
        'paper':             getattr(session, 'paper', None) or None,
        'timed':             bool(getattr(session, 'timed', False)),
        'total_questions':   session.total_questions,
        'correct_count':     session.correct_count,
        'started_at':        session.started_at.isoformat() if session.started_at else None,
        'finished_at':       session.finished_at.isoformat() if session.finished_at else None,
    }
    prefer = 'resolution=merge-duplicates, on-conflict=django_session_id'
    return _post('practice_sessions', payload, prefer=prefer)


def save_practice_answer_to_supabase(answer):
    """Save one PracticeAnswer row to Supabase (question from FK or from Supabase snapshot)."""
    q = answer.question
    session = answer.session
    if q:
        question_text = q.question_text or None
        correct_answer = q.correct_answer or None
        topic = getattr(q, 'topic', None) or None
    else:
        question_text = (answer.question_text or '').strip() or None
        correct_answer = (answer.correct_answer or '').strip() or None
        topic = None
    payload = {
        'django_session_id': session.id,
        'user_email':        getattr(answer.user, 'email', None),
        'question_text':     question_text,
        'chosen_answer':     answer.chosen_answer,
        'correct_answer':    correct_answer,
        'is_correct':        answer.is_correct,
        'program':           getattr(session, 'program', None) or None,
        'paper':             getattr(session, 'paper', None) or None,
        'topic':             topic,
        'answered_at':       answer.answered_at.isoformat() if answer.answered_at else None,
    }
    return _post('practice_answers', payload, prefer='return=minimal')


# ── Legacy aliases (so any old import still works) ────────────────────────────
sync_mcq_to_supabase              = save_mcq_to_supabase
sync_user_to_supabase             = save_user_to_supabase
sync_case_study_to_supabase       = save_case_study_to_supabase
sync_book_slide_to_supabase       = save_book_slide_to_supabase
sync_payment_to_supabase          = save_payment_to_supabase
sync_inquiry_to_supabase          = save_inquiry_to_supabase
sync_practice_session_to_supabase = save_practice_session_to_supabase
sync_practice_answer_to_supabase  = save_practice_answer_to_supabase
