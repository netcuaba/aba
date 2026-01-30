import sqlite3, os

db='transport.db' if os.path.exists('transport.db') else 'transport_backup.db'
print('db=', db)
conn=sqlite3.connect(db)
cur=conn.cursor()
cur.execute('PRAGMA table_info(accounts)')
cols=[r[1] for r in cur.fetchall()]
print('cols=', cols)

cur.execute("SELECT id, username, role, is_active, status, is_locked, password_hash, password FROM accounts WHERE username IN ('admin','lethihongthuan') ORDER BY username")
rows=[]
for r in cur.fetchall():
    ph=r[6] or ''
    pw=r[7] or ''
    rows.append((r[0], r[1], r[2], r[3], r[4], r[5], len(ph), len(pw)))
print('rows(id,username,role,is_active,status,is_locked,ph_len,pw_len)=', rows)

cur.execute('SELECT COUNT(*) FROM accounts')
print('accounts_count=', cur.fetchone()[0])
