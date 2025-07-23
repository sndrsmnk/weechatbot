def config(wcb):
    return {
        'events': ['irc_in2_PRIVMSG'],
        'commands': ['define', 'forget', 'si', 'is', 'search-info', 'info-search'],
        'permissions': ['user'],
        'help': "Get and set info items.\nBy default infoitems are kept per channel.\nSet 'bot_shared_knowledge' in config to True to disable."
    }


def do_search(wcb, event):
    search_for = event['command_args']

    db = wcb.db_connect()
    cur = db.cursor()
    sql = "SELECT DISTINCT item FROM wcb_infoitems WHERE value ILIKE %s"
    sql_args = ['%'+search_for+'%']

    if not wcb.state['bot_shared_knowledge']:
        sql += " AND channel = %s"
        sql_args.append(event['channel'])

    cur.execute(sql, sql_args)
    res = cur.fetchall()
    matching_items_array = []
    for val in res:
        matching_items_array.append(val[0])

    if not len(matching_items_array):
        return wcb.say("No matching info items found for your search string.")

    return wcb.say(["These info items match your search string:"] + matching_items_array)


def do_forget(wcb, event):
    if not wcb.perms('forget'):
        wcb.reply("you can't do that. Sorry.")
        return wcb.signal_stop
        
    re = wcb.re.compile('([^\s]+)\s(.*)')
    res = re.match(event['command_args'])
    if not res:
        wcb.reply("command unclear. Try '!forget <key> <[partof]value>'. Will remove all matching entries.")
        return wcb.signal_stop

    pub_k = res.group(1)
    db_k = res.group(1).lower()
    v = res.group(2)

    db = wcb.db_connect()
    cur = db.cursor()
    sql = "DELETE FROM wcb_infoitems WHERE item = %s AND value ILIKE %s"
    sql_args = [db_k, '%%'+v+'%%']
    if not wcb.state['bot_shared_knowledge']:
        sql += " AND channel = %s"
        sql_args.append(event['channel'])
    cur.execute(sql, sql_args)
    db.commit()
    wcb.reply("entry removed.")
    return wcb.signal_stop # prevent handling both the 'trigger' and the 'command' event.


def do_define(wcb, event):
    re = wcb.re.compile(wcb.state['bot_trigger_re'] + '(?:define\s)?(.+?) = (.*)')
    res = re.match(event['text'])
    pub_k = res.group(1)
    db_k = res.group(1).lower().strip()
    v = res.group(2)

    db = wcb.db_connect()
    cur = db.cursor()
    sql = "INSERT INTO wcb_infoitems (users_id, item, value, channel) VALUES (%s, %s, %s, %s)"
    cur.execute(sql, (event['user_info']['id'], db_k, v, event['channel']))
    db.commit()
    wcb.reply("entry added.")
    return wcb.signal_stop


def run(wcb, event):
    if event['command'] == 'forget':
        return do_forget(wcb, event)

    if event['command'] == 'define':
        return do_define(wcb, event)

    if event['command'] in ['si', 'is', 'search-info', 'info-search']:
        return do_search(wcb, event)

    # Process 'non command' triggers here
    txt = event['text']

    # See if it is an attempt to define a thing?
    re = wcb.re.compile(wcb.state['bot_trigger_re'] + '(?:define\s)?(.+?) = (.*)')
    res = re.match(txt)
    if res:
        return do_define(wcb, event)

    # See if it is an attempt to get the definition of a thing?
    re = wcb.re.compile(wcb.state['bot_trigger_re'] + '(.+?)\?\s*$')
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
        numres = len(res)
        defstr = []
        for val in res:
            defstr.append(val[0])

        if not defstr:
            if 'infoitem_auto_lookup_quiet' not in event:
                wcb.say(f"{pub_k} is not defined.")
            return wcb.signal_stop

        wcb.say([f"{pub_k} is"] + defstr)
        return wcb.signal_stop
