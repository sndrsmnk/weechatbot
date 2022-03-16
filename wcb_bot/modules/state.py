import json

def config(wcb):
    return {
        'events': [],
        'commands': ['save', 'set', 'set-json', 'get', 'del', 'list'],
        'permissions': ['owner'],
        'help': "Saves, sets and gets bot configuration"
    }


def run(wcb, event):
    if event['command'] == 'save':
        wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])
        wcb.save_obj_as_json(wcb.alarms, wcb.state['bot_alarms'])
        return wcb.say("Bot configuration saved!")

    if event['command'] == 'set-json':
        res = wcb.re.match("^([^\s]+)[\s=]+(.*)", event['command_args'])
        if not res:
            return wcb.say("Could not discern key, value from arguments: '%s'" % event['command_args'])

        k = res.group(1)
        v = res.group(2)

        ov = ''
        if k in wcb.state:
            ov = wcb.state[k]
        wcb.state[k] = json.loads(v)

        ret = "Set value of '%s' to '%s' in state." % (k, v)
        if ov:
            ret += " (old value: '%s')" % ov
        wcb.say("%s" % ret)
        return wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])

    if event['command'] == 'set':
        res = wcb.re.match("^([^\s]+)[\s=]+(.*)", event['command_args'])
        if not res:
            return wcb.say("Could not discern key, value from arguments: '%s'" % event['command_args'])

        k = res.group(1)
        v = res.group(2)

        if v.isnumeric(): v = int(v)
        elif v == 'True': v = True
        elif v == 'False': v = False

        ov = ''
        if k in wcb.state:
            ov = wcb.state[k]
        wcb.state[k] = v

        ret = "Set value of '%s' to '%s' in state." % (k, v)
        if ov:
            ret += " (old value: '%s')" % ov
        wcb.say("%s" % ret)
        return wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])


    if event['command'] == 'get':
        k = event['command_args']
        if k in wcb.state:
            return wcb.say("Set value of '%s' is '%s'." % (k, wcb.state[k]))
        else:
            return wcb.say("Key '%s' does not exist." % k)


    if event['command'] == 'del':
        k = event['command_args']
        if k not in wcb.state:
            return wcb.say("Key '%s' does not exist." % k)

        ov = wcb.state[k]
        del wcb.state[k]
        wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])
        return wcb.say("Key '%s' was removed! Value was: '%s'" % (k, ov))


    if event['command'] == 'list':
        keys = ", ".join(wcb.state.keys())
        return wcb.say("The following keys are in state: %s" % keys)
