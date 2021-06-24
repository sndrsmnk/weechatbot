def config(wcb):
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
        return wcb.say("Usage: merge irc_nick dbusername")

    merge_db_user = merge_db_user.lower()
    db = wcb.db_connect()
    cur = db.cursor()
    sql = "SELECT id, username FROM wcb_users WHERE username = %s"
    cur.execute(sql, (merge_db_user,))
    db_userinfo = cur.fetchone()
    if not db_userinfo:
        return wcb.say("User '%s' was not found in the database." % merge_db_user)

    merge_userhost = wcb.get_userhost_by_ircnick(merge_irc_nick)

    if not merge_userhost:
        return wcb.say("Nick '%s' was not found in channel '%s'." % (merge_irc_nick, event['channel']))

    # Don't merge users that are already identified.
    tmp = wcb.db_get_userinfo_by_userhost(merge_userhost)
    if tmp:
        return wcb.say("Hostmask '%s' for nick '%s' matches registered user '%s'." % (merge_userhost, merge_irc_nick, tmp['username']))

    sql = "INSERT INTO wcb_hostmasks (users_id, hostmask) VALUES (%s, %s)"
    cur.execute(sql, (db_userinfo[0], merge_userhost.lower()))

    db.commit()

    return wcb.say("Hostmask '%s' added to '%s', '%s' is now identified." % (merge_userhost, db_userinfo[1], merge_irc_nick))
