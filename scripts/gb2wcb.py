import time
from datetime import datetime
import psycopg2
import pymysql.cursors

dbi_h = 'gozerbot.db.source.host.tld'
dbi_u = 'botuser'
dbi_p = 'password'
dbi_d = 'botdatabase'

dbo_h = 'localhost'
dbo_u = 'weechatbotusr'
dbo_p = 'password'
dbo_d = 'weechatbotdb'

dbi = pymysql.connect(host=dbi_h, user=dbi_u, password=dbi_p, db=dbi_d, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
dbi_cur = dbi.cursor()

dbo = psycopg2.connect(host=dbo_h, user=dbo_u, password=dbo_p, dbname=dbo_d)
dbo_cur = dbo.cursor()

defchannel = '#bit.nl'
users = {}

#wcb_users
#wcb_perms - won't copy perms data, permissions are completely different
isql = "SELECT name FROM user"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['name'] = row['name'].lower()
    osql = "INSERT INTO wcb_users (username) VALUES (%s) ON CONFLICT (username) DO NOTHING RETURNING (id)"
    dbo_cur.execute(osql, (row['name'],))
    res = dbo_cur.fetchone()
    if not res:
        osql = "SELECT id FROM wcb_users WHERE username = %s"
        dbo_cur.execute(osql, (row['name'],))
        res = dbo_cur.fetchone()
    users[row['name']] = { 'id': res[0], 'userhosts': [] }
    osql = "INSERT INTO wcb_perms (users_id, permission) VALUES (%s, %s) ON CONFLICT (users_id, permission) DO NOTHING"
    dbo_cur.execute(osql, (res[0], 'user'))
dbo.commit()

#wcb_hostmasks
isql = "SELECT name, userhost FROM userhosts"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['name'] = row['name'].lower()
    row['userhost'] = row['userhost'].lower()
    osql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s) ON CONFLICT (hostmask) DO NOTHING RETURNING (id)"
    if row['name'] not in users:
        print("[hostmask] User '%s' for hostmask '%s' not found. Stale? -> skipped." % (row['name'], row['userhost']))
        continue # stale hostmask entry
    dbo_cur.execute(osql, (users[row['name']]['id'], row['userhost']))
    users[row['userhost']] = row['name']
    users[row['name']]['userhosts'].append(row['userhost'])
dbo.commit()

#wcb_infoitems
isql = "SELECT item, description, userhost, time FROM infoitems"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['item'] = row['item'].lower()
    row['userhost'] = row['userhost'].lower()
    osql = "INSERT INTO wcb_infoitems (users_id, item, value, channel, insert_time) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (item, value, channel) DO NOTHING"
    if row['userhost'] in users:
        users_id = users[users[row['userhost']]]['id']
    else:
        print("[infoitems] User hostmask '%s' does not match any user -> ghosted." % (row['userhost']))
        users_id = 1
    crtime = int(row['time'])
    if crtime <= 0 or crtime >= int(time.time()):
        crtime = int(time.time())
    db_datestr = datetime.utcfromtimestamp(crtime).strftime("%Y%m%d")
    dbo_cur.execute(osql, (users_id, row['item'], row['description'], defchannel, db_datestr))
dbo.commit()

#wcb_quotes
isql = "SELECT quote, createtime, nick FROM quotes"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['nick'] = row['nick'].lower()
    osql = "INSERT INTO wcb_quotes (users_id, quote, channel, insert_time) VALUES (%s, %s, %s, %s)"
    if row['nick'] in users:
        users_id = users[row['nick'].lower()]['id']
    else:
        print("[quotes] User hostmask '%s' does not match any user -> ghosted." % (row['nick']))
        users_id = 1
    crtime = int(row['createtime'])
    if crtime <= 0 or crtime >= int(time.time()):
        crtime = int(time.time())
    db_datestr = datetime.utcfromtimestamp(crtime).strftime("%Y%m%d")
    dbo_cur.execute(osql, (users_id, row['quote'], defchannel, db_datestr))
dbo.commit()

#wcb_karma
karma_id = {}
isql = "SELECT item, value FROM karma"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['item'] = row['item'].lower()
    osql = "INSERT INTO wcb_karma (item, karma, channel) VALUES (%s, %s, %s) ON CONFLICT (item, channel) DO NOTHING RETURNING (id)"
    dbo_cur.execute(osql, (row['item'], row['value'], defchannel))
    res = dbo_cur.fetchone()
    if not res:
        osql = "SELECT id FROM wcb_karma WHERE item = %s AND channel = %s"
        dbo_cur.execute(osql, (row['item'], defchannel))
        res = dbo_cur.fetchone()
    karma_id[row['item']] = res[0]
dbo.commit()

#ib_karma_who
isql = "SELECT item, nick, updown FROM whokarma"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['item'] = row['item'].lower()
    row['nick'] = row['nick'].lower()

    if row['item'] in karma_id:
        db_karma_id = karma_id[row['item']]
    else:
        print("[whokarma] Can't find item '%s' in karma -> skip." % row['item'])
        continue

    if row['nick'] in users:
        db_users_id = users[row['nick']]['id']
    else:
        print("[whokarma] Can't find user '%s' -> skip." % row['nick'])
        continue

    osql = """INSERT INTO wcb_karma_who (karma_id, users_id, direction, amount)
              VALUES (%s, %s, %s, %s)
              ON CONFLICT (karma_id, users_id, direction)
                  DO UPDATE SET amount = wcb_karma_who.amount + 1"""
    dbo_cur.execute(osql, (db_karma_id, db_users_id, row['updown'], 1))
dbo.commit()

#ib_karma_why
isql = "SELECT item, updown, why FROM whykarma"
dbi_cur.execute(isql)
rows = dbi_cur.fetchall()
for row in rows:
    row['item'] = row['item'].lower()

    if row['item'] in karma_id:
        db_karma_id = karma_id[row['item']]
    else:
        print("Can't find item '%s' in karma' -> skip." % row['item'])
        continue

    osql = """INSERT INTO wcb_karma_why (karma_id, direction, reason, channel)
              VALUES (%s, %s, %s, %s)
              ON CONFLICT (karma_id, direction, reason, channel)
                  DO NOTHING"""
    dbo_cur.execute(osql, (db_karma_id, row['updown'], row['why'], defchannel))
dbo.commit()
