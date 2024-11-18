def config(wcb):
    return {
        'events': [],
        'commands': ['mass-perm'],
        'permissions': ['mass-perm'],
        'help': "usage is mass-perm <add|remove> <permission1> [..<permissionN>] - mass-perms are always channel specific"
    }


def run(wcb, event):
    args_txt = event['command_args']
    args_txt = wcb.re.sub('\s{2,}', ' ', args_txt)
    args_arr = args_txt.split(' ')

    if len(args_arr) < 2:
        return wcb.reply(config(wcb)['help'])

    add_or_remove = args_arr.pop(0)
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
            wcb.weechat.infolist_free(infolist)
            return wcb.weechat.WEECHAT_RC_OK
        tuserhost = '%s!%s' %(nick, host)
        user_info = wcb.db_get_userinfo_by_userhost(tuserhost)
        if user_info and user_info['id']:
            if add_or_remove.lower() == 'add':
                sql = "INSERT INTO wcb_perms (users_id, permission, channel) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
            else:
                sql = "DELETE FROM wcb_perms WHERE users_id = %s AND permission = %s AND channel = %s"
            for perm in args_arr:
                cur.execute(sql, (user_info['id'], perm, event['channel']))
            db.commit()

    wcb.weechat.infolist_free(infolist)
    return wcb.reply("done. Or at least i tried.")

