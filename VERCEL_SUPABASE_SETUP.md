# Fix 500 / "Cannot connect to Supabase" on Vercel

The app **requires Supabase Postgres** on Vercel (SQLite causes crashes). Set **one** of these in **Vercel → Project → Settings → Environment Variables**:

---

## Option A: Connection string (recommended)

1. In **Supabase**: open your project → **Settings** (gear) → **Database**.
2. Under **Connection string**, choose **URI**.
3. Select **Transaction** (port **6543**) — not Session.
4. Copy the URI. It looks like:
   ```text
   postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with your **Database password** (from the same page).  
   If the password contains `@`, `#`, or `%`, URL-encode them: `@` → `%40`, `#` → `%23`, `%` → `%25`.
6. In **Vercel** add:
   - **Name:** `DATABASE_URL`
   - **Value:** the full URI (no quotes).

---

## Option B: Separate variables (no URL-encoding)

In Vercel, add these (from Supabase → Settings → Database):

| Name         | Example value                          |
|-------------|----------------------------------------|
| `DB_HOST`   | `aws-0-us-east-1.pooler.supabase.com` |
| `DB_PORT`   | `6543`                                 |
| `DB_NAME`   | `postgres`                             |
| `DB_USER`   | `postgres.xxxxxxxxxxxx` (with project ref) |
| `DB_PASSWORD` | your database password              |

Use **Transaction pooler** (port 6543) in the Supabase Database settings to get the correct host.

---

## After adding variables

1. **Redeploy** the project (Vercel → Deployments → ⋮ → Redeploy).
2. Open **Vercel → Project → Logs** (or **Functions → Logs**). You should see either:
   - `[DB] Using Postgres (Supabase)` or `[DB] Using Postgres via DB_HOST/DB_USER/DB_PASSWORD` → DB is configured.
   - `[DB] ERROR: On Vercel set DATABASE_URL...` or a traceback → fix the variable(s) and redeploy.

---

## Already set but still 500?

- **"DATABASE_URL parse failed"** → Use **Option B** (DB_HOST, DB_USER, DB_PASSWORD) so the password does not need URL-encoding.
- **"password authentication failed"** → Wrong DB password; copy it again from Supabase → Settings → Database.
- **"connection timed out" / "could not connect"** → Use the **Transaction pooler** host and port **6543**, not the direct connection (5432).
