def config(wcb):
    return {
        'events': [],
        'commands': ['chan-perm', 'chan-perms'],
        'permissions': ['perm'],
        'help': "usage is chan-perm <add|remove> <permission1> [..<permissionN>] - global perms are channel specific"
    }


def run(wcb, event):
    args_txt = event['command_args']
    args_txt = wcb.re.sub('\s{2,}', ' ', args_txt)
    args_arr = args_txt.split(' ')

    mode = 'list'
    if len(args_arr) > 0 and args_txt is not '':
        mode = args_arr.pop(0)
        wcb.mlog("derp --%s--" % mode)
    # args_arr should now only hold permissions to set

    if 'chan-perm' not in wcb.state:
        wcb.state['chan-perm'] = {}

    if wcb.event['channel'] not in wcb.state['chan-perm']:
        wcb.state['chan-perm'][wcb.event['channel']] = []

    if wcb.re.match('(?:list|show)', mode):
        counter = len(wcb.state['chan-perm'][wcb.event['channel']])
        if not counter:
            return wcb.say("No global permissions on '%s'" % wcb.event['channel'])
        return wcb.say("There's %s global permissions on '%s': %s" %
            (counter, wcb.event['channel'], sorted(wcb.state['chan-perm'][wcb.event['channel']])))

    if wcb.re.match('(?:set|add)', mode):
        counter = 0
        for permission in args_arr:
            wcb.state['chan-perm'][wcb.event['channel']].append(permission)
            counter += 1
        wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])
        return wcb.say("Added %d global permissions to '%s'" % (counter, wcb.event['channel']))

    elif wcb.re.match('(?:rem(?:ove)?|del(?:ete)?)', mode):
        counter = 0
        for permission in args_arr:
            if permission in wcb.state['chan-perm'][wcb.event['channel']]:
                wcb.state['chan-perm'][wcb.event['channel']].remove(permission)
                counter += 1
        wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])
        return wcb.say("Removed %d permissions from '%s'" % (counter, event['channel']))
