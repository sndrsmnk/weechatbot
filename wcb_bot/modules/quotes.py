import psycopg2cffi.extras
import random


def config(wcb):
    return {
        'events': [],
        'commands': [
            'aq', 'dq', # dq wants forget permission
            'lq', 'l3q', 'lq3',
            'rq', 'r3q', 'rq3',
            'iq', 'sq',
            'quote-who', 'quote-when',
            'q', 'quote'
            ],
        'permissions': ['user', 'forget'],
        'help': "Records and displays channel quotes"
    }


def run(wcb, event):

    db = wcb.db_connect()
    cur = db.cursor(cursor_factory = psycopg2cffi.extras.DictCursor)

    if event['command'] == 'aq':
        quote = event['command_args']
        sql = 'INSERT INTO wcb_quotes (users_id, quote, channel, insert_time) VALUES (%s, %s, %s, NOW()) RETURNING id'
        cur.execute(sql, (event['user_info']['id'], quote, event['channel']))
        res = cur.fetchone()
        if not res:
            return wcb.mlog("Error fetching quote id after insert.")
        db.commit()
        quote_id = res[0]
        return wcb.reply("quote #%s added!" % quote_id)

    if event['command'] == 'dq':
        if not wcb.perms('forget'):
            return

        quote_id = event['command_args']
        if not quote_id.isnumeric():
            return wcb.say("Argument must me quote id, not '%s'" % quote_id)

        sql = "DELETE FROM wcb_quotes WHERE id = %s"
        sql_args = [quote_id]
        if not wcb.state['bot_shared_knowledge']:
            sql += " AND channel = %s"
            sql_args.append(event['channel'])
        cur.execute(sql, sql_args)
        db.commit()
        return wcb.reply("quote #%s deleted." % quote_id)

    if event['command'] == 'iq':
        quote_id = event['command_args']
        if not quote_id.isnumeric():
            return wcb.say("Argument must me quote id, not '%s'" % quote_id)

        sql = "SELECT * FROM wcb_quotes WHERE id = %s"
        sql_args = [quote_id]
        if not wcb.state['bot_shared_knowledge']:
            sql += " AND channel = %s"
            sql_args.append(event['channel'])
        cur.execute(sql, sql_args)
        res = cur.fetchone()
        if not res:
            return wcb.reply("there is no quote with id #%s" % quote_id)

        wcb.say("#%s %s" % (res['id'], res['quote']))


    if event['command'] == 'sq':
        pattern = event['command_args']
        if not pattern or pattern == '':
            return wcb.reply("please specify a search pattern.")

        sql = "SELECT * FROM wcb_quotes WHERE quote ~* %s"
        sql_args = [pattern]
        if not wcb.state['bot_shared_knowledge']:
            sql += " AND channel = %s"
            sql_args.append(event['channel'])
        cur.execute(sql, sql_args)
        rows = cur.fetchall()
        if not rows:
            return wcb.reply("no quotes matched '%s'" % pattern)
        if len(rows) > 3: rows = random.sample(rows, 3)

        for row in rows:
            wcb.say("#%s %s" % (row['id'], row['quote']))
        return


    res = wcb.re.match(r'^(?:q|quote|rq|rq3|r3q)$', event['command'])
    if res:
        count = 1
        if '3' in event['command']:
            count = 3

        quote_ids = []
        sql = "SELECT id FROM wcb_quotes "
        sql_args = []
        if not wcb.state['bot_shared_knowledge']:
            sql += " WHERE channel = %s "
            sql_args.append(event['channel'])
        sql += "ORDER BY insert_time ASC"
        cur.execute(sql, sql_args)
        rows = cur.fetchall()
        for row in rows:
            quote_ids.append(row['id'])

        if len(quote_ids) < count:
            return wcb.reply("there's not enough quotes on %s for that." % event['channel'])

        rnd_ids = random.sample(quote_ids, count)
        sql = "SELECT * FROM wcb_quotes WHERE id = %s"
        for rnd_id in rnd_ids:
            cur.execute(sql, (rnd_id,))
            res = cur.fetchone()
            wcb.say("#%s %s" % (res['id'], res['quote']))
        return
    

    res = wcb.re.match(r'^(?:lq|l3q|lq3)$', event['command'])
    if res:
        count = 1
        if '3' in event['command']:
            count = 3

        sql = "SELECT * FROM wcb_quotes "
        sql_args = []
        if not wcb.state['bot_shared_knowledge']:
            sql += " WHERE channel = %s "
            sql_args.append(event['channel'])
        sql += "ORDER BY insert_time DESC LIMIT 3"
        cur.execute(sql, sql_args)
        rows = cur.fetchall()
        if not rows:
            return wcb.reply("there's no quotes on this channel.")

        counter = 0
        for row in rows:
            wcb.say("#%s %s" % (row['id'], row['quote']))
            counter += 1
            if counter == count: break
        return


    res = wcb.re.match(r'^quote-(?:who|when)$', event['command'])
    if res:
        quote_id = event['command_args']
        if not quote_id.isnumeric():
            return wcb.say("Argument must me quote id, not '%s'" % quote_id)

        sql = "SELECT wq.*, wu.username FROM wcb_quotes wq, wcb_users wu WHERE wq.users_id = wu.id"
        sql_args = []
        if not wcb.state['bot_shared_knowledge']:
            sql += " AND wq.channel = %s"
            sql_args.append(event['channel'])
        sql += " AND wq.id = %s"
        cur.execute(sql, (event['channel'], quote_id))
        row = cur.fetchone()
        if not row:
            return wcb.reply("no quote with that id was found.")

        return wcb.reply("quote #%s was added by %s on %s" % (row['id'], row['username'], row['insert_time']))
