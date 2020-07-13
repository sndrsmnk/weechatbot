def config():
    return {
        'events': [],
        'commands': ['meet'],
        'permissions': ['meet'],
        'help': "Introduce new users with 'meet'"
    }


def run(wcb, event):
    tnick = event['command_args']
    if tnick == '':
        return wcb.reply("please state who you want me to meet.")

    if tnick == event['bot_nick']:
        return wcb.reply("i know who i am.")

    tuserhost = wcb.get_userhost_by_ircnick(tnick)

    db_user_info = wcb.db_get_userinfo_by_userhost(tuserhost)
    if db_user_info != None:
        return wcb.reply("an existing user named '%s' was found matching the host mask '%s'." % (db_user_info['username'], tuserhost))

    db = wcb.db_connect()
    cur = db.cursor()

    sql = "INSERT INTO wcb_users (username) VALUES (%s)"
    cur.execute(sql, (tnick,))

    sql = "SELECT id FROM wcb_users WHERE username = %s"
    cur.execute(sql, (tnick,))
    res = cur.fetchone()
    if res == None:
        return wcb.mlog("Error looking up users_id!")

    tuserid = res[0]

    sql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s)"
    cur.execute(sql, (tuserid, tuserhost))

    sql = "INSERT INTO wcb_perms (users_id, permission) VALUES (%s, 'user')"
    cur.execute(sql, (tuserid,))

    db.commit()

    cur.close()
    db.close()

    return wcb.say("Added user '%s' to the database with host mask '%s'." % (tnick, tuserhost));
