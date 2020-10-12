def config(wcb):
    return {
        'events': [],
        'commands': ['mass-meet', 'mass-merge'],
        'permissions': ['mass-meet'],
        'help': "usage is mass-meet - merges users recognized by nick, meets new ones. use with care."
    }


def run(wcb, event):
    new = merged = recognized = 0
    db = wcb.db_connect()
    cur = db.cursor()

    # Find users on channel
    infolist = wcb.weechat.infolist_get('irc_nick', '', '%s,%s' % (event['server'], event['channel']))
    while wcb.weechat.infolist_next(infolist):
        nick = wcb.weechat.infolist_string(infolist, 'name')
        if nick == wcb.event['bot_nick']:
            continue
        host = wcb.weechat.infolist_string(infolist, 'host')
        if host == '':
            wcb.weechat.command(event['weechat_buffer'], '/who ' + event['channel'])
            wcb.say('OOPS: WeeChat stale data. Try again!')
            return wcb.weechat.WEECHAT_RC_OK
        tuserhost = host

        user_info_by_hostmask = wcb.db_get_userinfo_by_userhost(tuserhost)
        if user_info_by_hostmask and 'username' in user_info_by_hostmask:
            recognized += 1
            continue

        # XXX Wat als pietje op freenode een andere pietje is dan die op ircnet. :O
        wcb.say("%s" % nick)
        user_info_by_username = wcb.db_get_userinfo_by_username(nick)
        if user_info_by_username and 'username' in user_info_by_username:
            sql = "INSERT INTO ib_hostmasks (users_id, hostmask) VALUES (%s, %s)"
            cur.execute(sql, (user_info_by_username['id'], tuserhost))
            db.commit()
            merged += 1
            continue

        new += 1
        sql = "INSERT INTO wcb_users (username) VALUES (%s) RETURNING (id)"
        cur.execute(sql, (nick.lower(),))
        res = cur.fetchone()
        if res == None:
            wcb.mlog("Error looking up users_id after insert.")
            continue
        userid = res[0]
        sql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s)"
        cur.execute(sql, (userid, tuserhost.lower()))
        sql = "INSERT INTO wcb_perms (users_id, permission) VALUES (%s, 'user')"
        cur.execute(sql, (userid,))
        db.commit()

    rtxt = "done: %d new, %d merged and %d recognized." % (new, merged, recognized)
    return wcb.reply(rtxt)
