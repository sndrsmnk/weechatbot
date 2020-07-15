import psycopg2.extras


def config(wcb):
    return {
        'events': ['irc_in2_PRIVMSG'],
        'commands': [
            'karma', 'setkarma', 'set-karma',
            'who-karma-up', 'who-up', 'karma-who-up', 'karma-whoup',
            'who-karma-down', 'who-down', 'karma-who-down', 'karma-whodown',
            'why-karma-up', 'why-up', 'karma-why-up', 'karma-whyup',
            'why-karma-down', 'why-down', 'karma-why-down', 'karma-whydown',
            'goodness', 'badness',
            'fans', 'haters'
            ],
        'permissions': ['user', 'set-karma'],
        'help': "Keeps track of user karma"
    }


def run(wcb, event):
    # Exit early if event does not match the trigger regexp.
    if not wcb.re.match(wcb.state['bot_trigger_re'], event['text']):
        return
    # Strip off bot_trigger_re from text
    event['text'] = wcb.re.sub(wcb.state['bot_trigger_re'], '', event['text'])

    # We gonna need some DB yo.
    db = wcb.db_connect()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)

    # Check for a karma up / down event (eg, !foo++)
    res = wcb.re.match("^(.+?)\s*([\+\-]{2})(?:\s*#\s*(.*))?", event['text'])
    if res:
        item = res.group(1)
        direction = res.group(2)
        reason = res.group(3)

        update_sql = ''
        init_value = 0
        if direction == '++':
            direction = 'up'
            update_sql = 'karma = wcb_karma.karma + 1'
            init_value = 1
        else:
            direction = 'down'
            update_sql = 'karma = wcb_karma.karma - 1'
            init_value = -1

        # Update the karma.
        sql = "INSERT INTO wcb_karma (item, karma, channel) VALUES (%s, %s, %s) ON CONFLICT (item, channel) DO UPDATE SET " + update_sql + " RETURNING id, karma"
        cur.execute(sql, (item, init_value, event['channel']))
        db.commit()
        res = cur.fetchone()
        # Fetch the row id and karma value.
        karma_id = res[0]
        karma_value = res[1]

        # Store the 'who' info
        sql = "INSERT INTO wcb_karma_who (karma_id, users_id, direction, amount) VALUES (%s, %s, %s, 1) ON CONFLICT (karma_id, users_id, direction) DO UPDATE SET amount = wcb_karma_who.amount + 1"
        cur.execute(sql, (karma_id, event['user_info']['id'], direction))
        db.commit()

        # Store the 'why' info
        if reason and reason != '':
            sql = "INSERT INTO wcb_karma_why (karma_id, direction, reason, channel) VALUES (%s, %s, %s, %s) ON CONFLICT (karma_id, direction, reason, channel) DO UPDATE SET update_time = CURRENT_TIMESTAMP"
            cur.execute(sql, (karma_id, direction, reason, event['channel']))
            db.commit()

        rtxt = "karma for '%s' is now '%s'" % (item, karma_value)
        if reason: rtxt += " - %s" % reason
        return wcb.reply(rtxt)


    if event['command'] == 'karma':
        item = event['command_args']
        if item == '': return wcb.reply('please specify a karma item to lookup.')
        
        sql = "SELECT * FROM wcb_karma WHERE item = %s AND channel = %s"
        cur.execute(sql, (item, event['channel']))
        res = cur.fetchone()
        if not res:
            return wcb.reply("'%s' has no karma." % item)
        if res['karma'] != 0:
            return wcb.reply("karma for '%s' is %s" % (item, res['karma']))
        else:
            return wcb.reply("karma for '%s' is neutral" % item)


    res = wcb.re.match("^(?:karma-why|why-karma|why)\-?(up|down)", event['command'])
    if res:
        direction = res.group(1)
        item = event['command_args']
        if item == '': return wcb.reply('please specify a karma item to lookup.')

        sql = "SELECT * FROM wcb_karma WHERE item = %s AND channel = %s"
        cur.execute(sql, (item, event['channel']))
        karma_item = cur.fetchone()

        sql = "SELECT reason FROM wcb_karma_why WHERE karma_id = %s AND direction = %s AND channel = %s ORDER BY update_time DESC LIMIT 10"
        cur.execute(sql, (karma_item['id'], direction, event['channel']))
        karma_why_rows = cur.fetchall()
        why_arr = []
        if karma_why_rows:
            row_count = len(karma_why_rows)
            for row in karma_why_rows:
                why_arr.append(row['reason'])
            rtxt = ", ".join(why_arr)
            return wcb.reply("the %s most recent reason(s) for karma %s: %s" % (row_count, direction, rtxt))
        else:
            return wcb.reply("no reasons were given for karma %s" % direction)
    

    res = wcb.re.match("^(?:karma-who|who-karma|who)\-?(up|down)", event['command'])
    if res:
        direction = res.group(1)
        item = event['command_args']
        if item == '': return wcb.reply('please specify a karma item to lookup.')

        sql = "SELECT * FROM wcb_karma WHERE item = %s AND channel = %s"
        cur.execute(sql, (item, event['channel']))
        karma_item = cur.fetchone()
        if not karma_item:
            return wcb.reply("'%s' has no karma." % item)

        sql = """SELECT u.username, kwho.amount, k.item
               FROM wcb_users u, wcb_karma_who kwho, wcb_karma k
               WHERE u.id = kwho.users_id
               AND kwho.direction = %s
               AND k.id = kwho.karma_id
               AND k.id = %s"""
        cur.execute(sql, (direction, karma_item['id'],))
        karma_who_rows = cur.fetchall()
        who_arr = []
        row_count = len(karma_who_rows)
        for row in karma_who_rows:
            who_arr.append("%s(%s)" % (row['username'], row['amount']))
        rtxt = ", ".join(who_arr)
        return wcb.reply("the following person(s) brought the karma %s: %s" % (direction, rtxt))


    res = wcb.re.match("^(good|bad)ness", event['command'])
    if res:
        direction = res.group(1)
        sql_direction = "ASC"
        if direction == "good": sql_direction = "DESC" 

        sql = "SELECT item, karma FROM wcb_karma WHERE channel = %s ORDER BY karma " + sql_direction + " LIMIT 10"
        cur.execute(sql, (event['channel'],))
        rows = cur.fetchall()
        if not rows:
            return wcb.reply("there is no %sness here." % direction)

        rarr = []
        for row in rows:
            rarr.append("%s(%s)" % (row['item'], row['karma']))
        rtxt = "Karma %sness: " % direction
        rtxt += ", ".join(rarr)
        return wcb.say(rtxt)


    res = wcb.re.match("^(fans|haters)", event['command'])
    if res:
        direction = res.group(1)
        item = event['command_args']
        if item == '': return wcb.reply('please specify a karma item to lookup.')

        db_dir = "up"
        if direction == 'haters': db_dir = "down"

        sql = "SELECT * FROM wcb_karma WHERE item = %s AND channel = %s"
        cur.execute(sql, (item, event['channel']))
        karma_item = cur.fetchone()
        if not karma_item:
            return wcb.reply("no such karma item, '%s'" % item)

        sql = """SELECT kw.id AS wcb_karma_who_id,
                    kw.amount AS amount,
                    u.id AS wcb_users_id,
                    u.*
            FROM wcb_karma_who kw, wcb_users u
            WHERE u.id = kw.users_id
                AND karma_id = %s
                AND direction = %s
            ORDER BY amount DESC LIMIT 10"""
        cur.execute(sql, (karma_item['id'], db_dir))
        rows = cur.fetchall()
        rarr = []
        for row in rows:
            rarr.append("%s(%s)" % (row['username'], row['amount']))
        rtxt = "%s of %s: %s" % (direction, item, ', '.join(rarr))
        return wcb.reply(rtxt)


    res = wcb.re.match("^set\-?karma\s+(.+?)\s+([-0-9]+)", event['text'])
    if res:
        if not wcb.perms(["owner", "set-karma"]): return wcb.reply("i can't let you do that.")
        item = res.group(1)
        value = res.group(2)

        sql = "INSERT INTO wcb_karma (item, karma, channel) VALUES (%s, %s, %s) ON CONFLICT (item, channel) DO UPDATE SET karma = %s"
        cur.execute(sql, (item, value, event['channel'], value))
        db.commit()
        return wcb.reply("ok.")


    wcb.mlog("unhandled..." + event['text'])

