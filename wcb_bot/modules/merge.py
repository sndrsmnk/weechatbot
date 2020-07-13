def config():
    return {
        'events': [],
        'commands': ['merge'],
        'permissions': ['merge'],
        'help': "'Merge' the hostmask of a IRC-user to a database user"
    }


def run(wcb, event):
    try:
        merge_irc_nick, merge_db_user = event['command_args'].split(' ')
    except ValueError as err:
        wcb.say("Usage: merge irc_nick dbusername")
        return wcb.weechat.WEECHAT_RC_OK
    
    db = wcb.db_connect()
    cur = db.cursor()
    sql = "SELECT id, username FROM wcb_users WHERE username = %s"
    cur.execute(sql, (merge_db_user,))
    db_userinfo = cur.fetchone()
    if not db_userinfo:
        wcb.say("User '%s' was not found in the database." % merge_db_user)
        return wcb.weechat.WEECHAT_RC_OK

    merge_userhost = wcb.get_userhost_by_ircnick(merge_ircnick)

    if not merge_userhost:
        wcb.say("Nick '%s' was not found in channel '%s.'" % (merge_irc_nick, event['channel']))

    # Don't merge users that are already identified.
    tmp = wcb.db_get_userinfo_by_userhost(merge_userhost)
    if tmp:
        wcb.say("Hostmask '%s' for nick '%s' matches registered user '%s'." % (merge_userhost, merge_irc_nick, tmp['username']))
        return wcb.weechat.WEECHAT_RC_OK

    sql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s)"
    cur.execute(sql, (db_userinfo[0], merge_userhost))

    db.commit()

    wcb.say("Hostmask '%s' added to '%s', '%s' is now identified." % (merge_userhost, db_userinfo[1], merge_irc_nick))
