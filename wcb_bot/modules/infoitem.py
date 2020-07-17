def config(wcb):
    return {
        'events': ['irc_in2_PRIVMSG'],
        'commands': [],
        'permissions': ['user'],
        'help': "Get and set info items.\nBy default infoitems are kept per channel.\nSet 'bot_shared_knowledge' in config to True to disable."
    }


def run(wcb, event):
    if event['command'] == 'forget':
        if not wcb.perms('forget'):
            return wcb.reply("you can't do that. Sorry.")
            
        re = wcb.re.compile('([^\s]+)\s(.*)')
        res = re.match(event['command_args'])
        if res:
            pub_k = res.group(1)
            db_k = res.group(1).lower()
            v = res.group(2)

            db = wcb.db_connect()
            cur = db.cursor()
            sql = "DELETE FROM wcb_infoitems WHERE item = %s AND channel = %s AND value LIKE %s"
            cur.execute(sql, (db_k, event['channel'], '%'+v+'%'))
            db.commit()
            return wcb.reply("entry removed.")
        else:
            return wcb.reply("command unclear. Try '!forget <key> <[partof]value>'. Will remove all matching entries.")


    if event['trigger'] == 'event':
        txt = event['text']

        # See if it is an attempt to define a thing?
        re = wcb.re.compile(wcb.state['bot_trigger_re'] + '(.+?) = (.*)')
        res = re.match(txt)
        if res:
            pub_k = res.group(1)
            db_k = res.group(1).lower()
            v = res.group(2)
            
            db = wcb.db_connect()
            cur = db.cursor()
            sql = "INSERT INTO wcb_infoitems (users_id, item, value, channel) VALUES (%s, %s, %s, %s)"
            cur.execute(sql, (event['user_info']['id'], db_k, v, event['channel']))
            db.commit()
            return wcb.reply("entry added.")

        # See if it is an attempt to get the definition of a thing?
        re = wcb.re.compile(wcb.state['bot_trigger_re'] + '(.+?)\?$')
        res = re.match(txt)
        if res:
            pub_k = res.group(1)
            db_k = res.group(1).lower()
            
            db = wcb.db_connect()
            cur = db.cursor()

            sql = "SELECT value FROM wcb_infoitems WHERE item = %s"
            sql_args = [db_k]

            if not wcb.state['bot_shared_knowledge']:
                sql += " AND channel = %s"
                sql_args.append(event['channel'])

            sql += " ORDER BY insert_time ASC"

            cur.execute(sql, sql_args)
            res = cur.fetchall()
            defstr = []
            for val in res:
                defstr.append(val[0])
            retstr = " .. ".join(defstr)
            if retstr == '':
                return wcb.say('%s is not defined.' % pub_k)
            return wcb.say("%s is %s" % (pub_k, retstr))
