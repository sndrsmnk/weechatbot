def config(wcb):
    return {
        'events': [],
        'commands': ['perm', 'perms'],
        'permissions': ['perm'],
        'help': "usage is perm <add|remove> <nick> <permission1> [..<permissionN>] [<channel>] - leave channel out for global permission."
    }


def run(wcb, event):
    args_txt = event['command_args']
    args_txt = wcb.re.sub('\s{2,}', ' ', args_txt)
    args_arr = args_txt.split(' ')

    if len(args_arr) < 3:
        return wcb.reply("usage is perm <add|remove> <nick> <permission1> [..<permissionN>] [<channel>]")

    mode = args_arr.pop(0)
    nick = args_arr.pop(0)
    channel = ''
    if wcb.re.match('^[#&]', args_arr[-1]):
        channel = args_arr.pop(-1)

    # args_arr should now only hold permissions to set

    nick_userinfo = wcb.db_get_userinfo_by_ircnick(nick)
    if not nick_userinfo:
        return wcb.say("Could not match nick '%s' to a known user. Try merging first?" % nick)

    db = wcb.db_connect()
    cur = db.cursor()

    if wcb.re.match('(?:set|add)', mode):
        counter = 0
        sql = "INSERT INTO wcb_perms (users_id, permission, channel) VALUES (%s, %s, %s)"
        for permission in args_arr:
            cur.execute(sql, (nick_userinfo['id'], permission, channel.lower()))
            counter += 1
        db.commit(); cur.close(); db.close()
        return wcb.say("Added %d permissions to '%s'" % (counter, nick))

    elif wcb.re.match('(?:rem(?:ove)?|del(?:ete)?)', mode):
        counter = 0
        sql = "DELETE FROM wcb_perms WHERE users_id = %s AND permission = %s AND channel = %s"
        for permission in args_arr:
            cur.execute(sql, (nick_userinfo['id'], permission, channel.lower()))
            counter += 1
        db.commit(); cur.close(); db.close()
        return wcb.say("Removed %d permissions from '%s'" % (counter, nick))
