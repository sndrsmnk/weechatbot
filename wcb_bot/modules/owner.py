def config(wcb):
    return {
        'events': [],
        'commands': ['owner'],
        'permissions': [],
        'help': "Helps with claiming bot ownership when the bot has not been claimed before\nUsage: !owner <bot_uniqueid>",
    }


def run(wcb, event):
    if wcb.state['bot_ownermask'] != '' and wcb.state['bot_ownermask'] != event['host']:
        return wcb.reply("no you're not.")

    if wcb.state['bot_ownermask'] != '' and wcb.state['bot_ownermask'] == event['host']:
        return wcb.reply("yes you are!")

    if event['command_args'] != wcb.state['bot_uniqueid']:
        return wcb.reply("sorry, that is not the correct id to win my heart.")

    tuserhost =  wcb.get_userhost_by_ircnick(event['nick'])
    if not tuserhost:
        return wcb.say("Failed to look up your userhost by irc nick. Investigate!")

    db = wcb.db_connect()
    cur = db.cursor()

    sql = "INSERT INTO wcb_users (username) VALUES (%s)"
    cur.execute(sql, (event['nick'],))

    sql = "SELECT id FROM wcb_users WHERE username = %s"
    cur.execute(sql, (event['nick'],))
    res = cur.fetchone()
    if res == None:
        return wcb.mlog("Error looking up users_id!")

    tuserid = res[0]

    sql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s)"
    cur.execute(sql, (tuserid, tuserhost))

    sql = "INSERT INTO wcb_perms (users_id, permission) VALUES (%s, 'owner')"
    cur.execute(sql, (tuserid,))

    db.commit()

    cur.close()
    db.close()

    wcb.state['bot_ownermask'] = event['host']
    wcb.load_all_modules()
    wcb.save_bot_configuration()
    return wcb.say("Hi! You are now my owner!")
