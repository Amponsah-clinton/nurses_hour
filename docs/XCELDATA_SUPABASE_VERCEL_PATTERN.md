# How xceldata Connects to Supabase on Vercel

This doc summarizes how the **xceldata** project does computations and talks to Supabase when deployed on Vercel, so you can align NurseHour (wiser) with the same pattern.

---

## 1. Settings (Django + Supabase)

**File: `xceldata/aitech_site/settings.py`**

- **Database:** SQLite only. On Vercel: `NAME: '/tmp/db.sqlite3'`; locally: `BASE_DIR / 'db.sqlite3'`.
- **Sessions:** Signed cookies (no DB table needed):
  - `SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'`
  - `SESSION_SAVE_EVERY_REQUEST = True`
- **Supabase:** Env vars only (no Django DB for app data):
  - `SUPABASE_URL`, `SUPABASE_KEY` (anon), `SUPABASE_SERVICE_KEY` (service role)
  - `SUPABASE_STORAGE_BUCKET` for uploads
- **Static:** WhiteNoise, `STATICFILES_DIRS = [BASE_DIR]`, `STATIC_ROOT = .../staticfiles`
- **Build on Vercel:** `"buildCommand": "python manage.py collectstatic --noinput"` (no migrate in build)

So: **Django = auth/sessions/cookies + routing; Supabase = all app data (users, orders, contacts, etc.).**

---

## 2. Supabase Client (Backend)

**File: `xceldata/website/supabase_client.py`**

- Single lazy client using **service role** key (bypasses RLS).
- Used only on the server (never expose service key to frontend).

```python
from django.conf import settings

_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
    return _supabase_client
```

**Dependency:** `supabase>=2.0.0` in `requirements.txt`.

---

## 3. How “Computations” Work (Views → Supabase)

All app data lives in Supabase. Views do the “computations” by:

1. Calling **`get_supabase()`** to get the client.
2. Using the **Supabase client** to read/write tables (no Django ORM for that data).
3. Optionally calling **external APIs** (e.g. DataHub bundles), then merging with Supabase data.

**Examples from xceldata:**

| What | How |
|------|-----|
| **Contact form** | `get_supabase().table('contacts').insert({...}).execute()` |
| **Bundles by network** | DataHub API via `datahub_bundles.get_datahub_bundles()`; price overrides from `sb.table('bundle_price_overrides').select(...).execute()`; merge in Python. |
| **User transactions** | `sb.table('orders').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()`; optionally join bundle names from `sb.table('bundles')`. |
| **Admin dashboard** | `sb.table('users').select(...)`, `sb.table('orders').select(...)`, `sb.table('wallets')`, `sb.table('payments')`; aggregate in Python (totals, balances, recent orders). |
| **Excel export** | Build data from Supabase tables, then use `openpyxl` to generate the file. |

So “computations” = **Supabase reads/writes + Python logic + optional external APIs**; no Django models for that data.

---

## 4. Vercel Setup (xceldata)

**File: `xceldata/vercel.json`**

```json
{
  "builds": [{ "src": "api/index.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "api/index.py" }],
  "buildCommand": "python manage.py collectstatic --noinput"
}
```

- **No `migrate` in build.** SQLite in `/tmp` is ephemeral; xceldata doesn’t rely on Django DB for app data, only for auth/sessions, and uses signed-cookie sessions so it can work even when `/tmp` is empty.
- **Entry:** `api/index.py` exposes the Django WSGI app:

```python
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aitech_site.settings')
app = get_wsgi_application()
```

- **Env on Vercel:** `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY` (and any other keys) set in the Vercel project.

---

## 5. Applying This to NurseHour (wiser)

To connect NurseHour to Supabase on Vercel in the same way:

1. **Keep Supabase for app data**  
   You already sync inquiries, payments, users, etc. to Supabase via `website/supabase_sync.py`. That’s the same idea as xceldata: app data in Supabase.

2. **Optional: Supabase Python client**  
   If you want to *read* from Supabase in views (e.g. show inquiries from Supabase instead of Django DB), add a small client like xceldata’s:
   - `pip install supabase`
   - Add `website/supabase_client.py` with `get_supabase()` using `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.
   - In views, use `get_supabase().table('inquiries').select(...).execute()` etc. You already do HTTP-based sync in `supabase_sync.py`; the client is just a cleaner option for more reads/writes.

3. **Vercel build**  
   xceldata uses **only** `collectstatic` in the build and **no** migrate. That works because:
   - Sessions = signed cookies (no DB).
   - App data = Supabase.

   NurseHour currently uses Django auth (user table) and SQLite. So you either:
   - **Option A:** Use **Supabase PostgreSQL** as Django’s DB on Vercel (`DATABASE_URL`), run `migrate` once (or in build), and keep auth in Postgres; or  
   - **Option B:** Keep SQLite + build-time migrate + copy `db.sqlite3` to `/tmp` in `wsgi.py` (what we did in wiser) so auth works.

4. **Env on Vercel**  
   Set the same Supabase vars you use in xceldata: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, and (if you use it) `DATABASE_URL` for Postgres when you switch.

---

## 6. Summary Table

| Aspect | xceldata | NurseHour (wiser) |
|--------|----------|-------------------|
| Django DB | SQLite (`/tmp` on Vercel) | SQLite (bundle + copy to `/tmp`) or Postgres |
| Sessions | Signed cookies | Signed cookies |
| App data | 100% Supabase (tables: users, orders, contacts, etc.) | Supabase sync (inquiries, payments, users, etc.) |
| Backend Supabase | `supabase` lib + `get_supabase()` | HTTP in `supabase_sync.py` (or add `supabase` client) |
| Build (Vercel) | `collectstatic` only | `build_files.sh` (migrate + collectstatic) or Postgres + migrate |
| Computations | Supabase queries + Python + DataHub API | Django ORM + Supabase sync; can add more Supabase reads in views |

Using the xceldata pattern on NurseHour means: **treat Supabase as the source of truth for app data**, use **signed-cookie sessions**, and either **Supabase Postgres for Django** or **build-time migrate + copy SQLite** so login works on Vercel.
