import time
usleep = lambda x: time.sleep(x/1000.0)


def config():
    return {
        'events': [],
        'commands': ['meet'],
        'permissions': ['meet', 'merge'],
        'help': "Introduce new users with 'meet'"
    }


def run(wcb, event):
    # Refresh WeeChat internal information about channel participants
    wcb.weechat.command(event['weechat_buffer'], '/who ' + event['channel'])
    usleep(500)

    tnick = event['command_args']
    if tnick == '':
        wcb.reply("please state who you want me to meet.")
        return wcb.weechat.WEECHAT_RC_OK

    if tnick == event['bot_nick']:
        wcb.reply("i know who i am.")
        return wcb.weechat.WEECHAT_RC_OK

    # Find referenced nick name in the originating event channel
    infolist = wcb.weechat.infolist_get('irc_nick', '', '%s,%s' % (event['server'], event['channel']))
    tuserhost = ''
    while wcb.weechat.infolist_next(infolist):
        nick = wcb.weechat.infolist_string(infolist, 'name')
        if nick != tnick:
            continue
        host = wcb.weechat.infolist_string(infolist, 'host')
        if host == '':
            wcb.say("Sorry, try that again?")
            return wcb.weechat.WEECHAT_RC_OK
        tuserhost = '%s!%s' %(nick, host)                
    wcb.weechat.infolist_free(infolist)

    db_user_info = wcb.db_get_userinfo(tuserhost)
    if db_user_info != None:
        wcb.reply("an existing user named '%s' was found matching the host mask '%s'." % (db_user_info['username'], tuserhost))
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
