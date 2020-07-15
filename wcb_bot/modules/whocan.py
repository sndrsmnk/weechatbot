def config(wcb):
    return {
        'events': [],
        'commands': ['whocan', 'who-can'],
        'permissions': ['user'],
        'help': "Test"
    }


def run(wcb, event):
    whocan_perm = event['command_args']
    if not whocan_perm or whocan_perm == '':
        return wcb.reply("i need a permission to look for.")

    db = wcb.db_connect()
    cur = db.cursor()
    sql = """SELECT DISTINCT(wu.username)
        FROM wcb_users wu
        LEFT JOIN wcb_perms wp
        ON wu.id = wp.users_id
        WHERE
            (wp.permission = %s OR wp.permission = 'owner')
            AND (wp.channel = %s OR wp.channel = '')"""
    cur.execute(sql, (whocan_perm, event['channel']))
    res = cur.fetchall()
    thesecan = []
    for val in res:
        thesecan.append(val[0])
    
    if not thesecan:
        return wcb.reply("nobody has '%s' as a permission here." % whocan_perm)

    return wcb.reply("the following people can '%s' here: %s" % (whocan_perm, ", ".join(thesecan)))
