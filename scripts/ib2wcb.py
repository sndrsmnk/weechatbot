import time
from datetime import datetime
import psycopg2cffi
import pymysql.cursors

dbi_h = 'irssibot.db.source.host.tld'
dbi_u = 'botuser'
dbi_p = 'password'
dbi_d = 'botdatabase'

dbo_h = 'localhost'
dbo_u = 'weechatbotusr'
dbo_p = 'password'
dbo_d = 'weechatbotdb'

dbi = pymysql.connect(host=dbi_h, user=dbi_u, password=dbi_p, db=dbi_d, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
dbi_cur = dbi.cursor()

dbo = psycopg2cffi.connect(host=dbo_h, user=dbo_u, password=dbo_p, dbname=dbo_d)
dbo_cur = dbo.cursor()

defchannel = '#bit.nl'
users = {}

#wcb_users
#wcb_perms - won't copy perms data, permissions are completely different
isql = "SELECT id, ircnick AS name FROM ib_users"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    if row['id'] == 1: continue
    row['name'] = row['name'].lower()
    osql = "INSERT INTO wcb_users (id, username) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING RETURNING (id)"
    dbo_cur.execute(osql, (row['id'], row['name'],))
    users[row['name']] = { 'id': row['id'], 'userhosts': [] }
    users[row['id']] = row['name']
dbo.commit()

#wcb_perms
isql = "SELECT users_id, permission FROM ib_perms"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    if row['users_id'] == 1: continue
    osql = "INSERT INTO wcb_perms (users_id, permission) VALUES (%s, %s) ON CONFLICT (users_id, permission) DO NOTHING RETURNING (id)"
    dbo_cur.execute(osql, (row['users_id'], row['permission']))
dbo.commit()

#wcb_hostmasks
isql = "SELECT users_id, hostmask FROM ib_hostmasks"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['hostmask'] = row['hostmask'].lower()
    osql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s) ON CONFLICT (hostmask) DO NOTHING RETURNING (id)"
    if row['users_id'] not in users:
        print("[hostmask] User '%s' for hostmask '%s' not found. Stale? -> skipped." % (row['users_id'], row['hostmask']))
        continue # stale hostmask entry
    dbo_cur.execute(osql, (row['users_id'], row['hostmask']))
    users[row['hostmask']] = row['users_id']
dbo.commit()

#wcb_infoitems
isql = "SELECT users_id, item, value, channel, insert_time FROM ib_infoitems"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['item'] = row['item'].lower()
    row['channel'] = row['channel'].lower()
    osql = "INSERT INTO wcb_infoitems (users_id, item, value, channel, insert_time) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (item, value, channel) DO NOTHING"
    crtime = row['insert_time'].strftime("%Y%m%d")
#    if crtime <= 0 or crtime >= int(time.time()):
#        crtime = int(time.time())
#    db_datestr = datetime.utcfromtimestamp(crtime).strftime("%Y%m%d")
    dbo_cur.execute(osql, (row['users_id'], row['item'], row['value'], row['channel'], crtime))
dbo.commit()

#wcb_quotes
isql = "SELECT users_id, quote, channel, insert_time FROM ib_quotes"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['channel'] = row['channel'].lower()
    osql = "INSERT INTO wcb_quotes (users_id, quote, channel, insert_time) VALUES (%s, %s, %s, %s)"
    crtime = row['insert_time'].strftime("%Y%m%d")
    dbo_cur.execute(osql, (row['users_id'], row['quote'], row['channel'], crtime))
dbo.commit()

#wcb_karma
karma_id = {}
isql = "SELECT id, item, karma, channel FROM ib_karma"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['item'] = row['item'].lower()
    osql = "INSERT INTO wcb_karma (id, item, karma, channel) VALUES (%s, %s, %s, %s) ON CONFLICT (item, channel) DO NOTHING RETURNING (id)"
    dbo_cur.execute(osql, (row['id'], row['item'], row['karma'], row['channel']))
dbo.commit()

#wcb_karma_who
isql = "SELECT karma_id, users_id, direction, amount, update_time FROM ib_karma_who"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    if row['direction'] == '': continue
    osql = """INSERT INTO wcb_karma_who (karma_id, users_id, direction, amount, update_time)
              VALUES (%s, %s, %s, %s, %s)
              ON CONFLICT (karma_id, users_id, direction)
                  DO UPDATE SET amount = wcb_karma_who.amount + 1"""
    dbo_cur.execute(osql, (row['karma_id'], row['users_id'], row['direction'], 1, row['update_time']))
dbo.commit()

#ib_karma_why
isql = "SELECT karma_id, direction, reason, channel, update_time FROM ib_karma_why"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    if row['direction'] == '': continue
    osql = """INSERT INTO wcb_karma_why (karma_id, direction, reason, channel, update_time)
              VALUES (%s, %s, %s, %s, %s)
              ON CONFLICT (karma_id, direction, reason, channel)
                  DO NOTHING"""
    dbo_cur.execute(osql, (row['karma_id'], row['direction'], row['reason'], row['channel'], row['update_time']))
dbo.commit()
