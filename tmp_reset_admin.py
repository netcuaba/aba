import sqlite3, os, base64, hashlib, secrets

def hash_password(password: str, iterations: int = 210_000) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return 'pbkdf2_sha256$%d$%s$%s' % (
        iterations,
        base64.b64encode(salt).decode('ascii'),
        base64.b64encode(dk).decode('ascii'),
    )

db = 'transport.db' if os.path.exists('transport.db') else ('transport_backup.db' if os.path.exists('transport_backup.db') else None)
print('db=', db)
if not db:
    raise SystemExit('No sqlite db found')

conn = sqlite3.connect(db)
cur = conn.cursor()

new_hash = hash_password('Badaica1')
# accounts.password is NOT NULL in this DB, so keep plaintext in password too (legacy), but login will still upgrade/verify via hash.
cur.execute("UPDATE accounts SET password_hash=?, password=?, is_active=1, status='Active', is_locked=0 WHERE username='admin'", (new_hash, 'Badaica1'))
conn.commit()

cur.execute("SELECT id, username, role, is_active, status, is_locked, LENGTH(password_hash), LENGTH(password) FROM accounts WHERE username='admin'")
print('admin_row=', cur.fetchone())
print('reset_ok=1')
