def config():
    return {
        'events': [],
        'commands': ['deluser'],
        'permissions': ['deluser'],
        'help': "Introduce new users with 'meet'"
    }


def run(wcb, event):
    tnick = event['command_args']
    if tnick == '':
        wcb.reply("please state who you want me to delete.")
        return wcb.weechat.WEECHAT_RC_OK

    if tnick == event['bot_nick']:
        wcb.reply("why are you so mean. :(")
        return wcb.weechat.WEECHAT_RC_OK

    db_user_info = wcb.db_get_userinfo_by_ircnick(tnick)
    if db_user_info == None:
        wcb.reply("no user named '%s' was found." % (db_user_info['username'], tuserhost))
        return wcb.weechat.WEECHAT_RC_OK

    db = wcb.db_connect()
    cur = db.cursor()

    sql = "INSERT INTO wcb_users (username) VALUES (%s)"
    cur.execute(sql, (tnick,))

    sql = "SELECT id FROM wcb_users WHERE username = %s"
    cur.execute(sql, (tnick,))
    res = cur.fetchone()
    if res == None:
        wcb.mlog("Error looking up users_id!")
        return wcb.weechat.WEECHAT_RC_ERROR
    tuserid = res[0]

    sql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s)"
    cur.execute(sql, (tuserid, tuserhost))

    sql = "INSERT INTO wcb_perms (users_id, permission) VALUES (%s, 'user')"
    cur.execute(sql, (tuserid,))

    db.commit()

    cur.close()
    db.close()

    wcb.say("Added user '%s' to the database with host mask '%s'." % (tnick, tuserhost));
    return wcb.weechat.WEECHAT_RC_OK
