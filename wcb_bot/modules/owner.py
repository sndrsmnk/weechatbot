def config():
    return {
        'events': [],
        'commands': ['owner'],
        'permissions': [],
        'help': "Helps with claiming bot ownership when the bot has not been claimed before\nUsage: !owner <bot_uniqueid>",
    }


def run(wcb, event):
    if wcb.state['bot_ownermask'] != '' and wcb.state['bot_ownermask'] != event['host']:
        wcb.reply("no you're not.")
        return wcb.weechat.WEECHAT_RC_OK

    if wcb.state['bot_ownermask'] != '' and wcb.state['bot_ownermask'] == event['host']:
        wcb.reply("yes you are!")
        return wcb.weechat.WEECHAT_RC_OK

    if event['command_args'] != wcb.state['bot_uniqueid']:
        wcb.reply("sorry, that is not the correct id to win my heart.")
        return wcb.weechat.WEECHAT_RC_OK

    tuserhost =  wcb.get_userhost_by_ircnick(event['nick'])
    if not tuserhost:
        wcb.say("Failed to look up your userhost by irc nick. Investigate!")
        return wcb.weechat.WEECHAT_RC_ERROR

    db = wcb.db_connect()
    cur = db.cursor()

    sql = "INSERT INTO wcb_users (username) VALUES (%s)"
    cur.execute(sql, (event['nick'],))

    sql = "SELECT id FROM wcb_users WHERE username = %s"
    cur.execute(sql, (event['nick'],))
    res = cur.fetchone()
    if res == None:
        wcb.mlog("Error looking up users_id!")
        return wcb.weechat.WEECHAT_RC_ERROR
    tuserid = res[0]

    sql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s)"
    cur.execute(sql, (tuserid, tuserhost))

    sql = "INSERT INTO wcb_perms (users_id, permission) VALUES (%s, 'owner')"
    cur.execute(sql, (tuserid,))

    db.commit()

    cur.close()
    db.close()

    wcb.say("Hi! You are now my owner!")
    wcb.state['bot_ownermask'] = event['host']
    wcb.load_all_modules()
    wcb.save_bot_configuration()
    return wcb.weechat.WEECHAT_RC_OK
