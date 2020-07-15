def config(wcb):
    return {
        'events': [],
        'commands': ['deluser'],
        'permissions': ['deluser'],
        'help': "Introduce new users with 'meet'"
    }


def run(wcb, event):
    tnick = event['command_args']
    if tnick == '':
        return wcb.reply("please state who you want me to delete.")

    if tnick == event['bot_nick']:
        return wcb.reply("why are you so mean. :(")

    db_user_info = wcb.db_get_userinfo_by_ircnick(tnick)
    if db_user_info == None:
        return wcb.reply("no user named '%s' was found." % (tnick))

    db = wcb.db_connect()
    cur = db.cursor()

    sql = "DELETE FROM wcb_hostmasks WHERE users_id = %s"
    cur.execute(sql, (db_user_info['id'],))
    sql = "DELETE FROM wcb_perms WHERE users_id = %s"
    cur.execute(sql, (db_user_info['id'],))
    sql = "DELETE FROM wcb_users WHERE id = %s"
    cur.execute(sql, (db_user_info['id'],))

    db.commit()

    return wcb.say("Obliteratred user '%s' from existence.." % tnick);
