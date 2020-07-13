def config():
    return {
        'events': [],
        'commands': ['save', 'set', 'get', 'del', 'list'],
        'permissions': ['save', 'set', 'get', 'del', 'list'],
        'help': "Saves, sets and gets bot configuration"
    }


def run(wcb, event):
    if event['command'] == 'save':
        wcb.save_bot_configuration()
        return wcb.say("Bot configuration saved!")

    if event['command'] == 'set':
        res = wcb.re.match("^([^\s]+)[\s=]+(.*)", event['command_args'])
        if res:
            k = res.group(1)
            v = res.group(2)
            ov = ''
            if k in wcb.state:
                ov = wcb.state[k]
            wcb.state[k] = v
            ret = "Set value of '%s' to '%s' in state." % (k, v)
            if ov:
                ret += " (old value: '%s')" % ov
            wcb.say("%s" % ret)
            return wcb.save_bot_configuration()
        return wcb.say("Could not discern key, value from arguments: '%s'" % event['command_args'])
            
    if event['command'] == 'get':
        k = event['command_args']
        if k in wcb.state:
            return wcb.say("Set value of '%s' is '%s'." % (k, wcb.state[k]))
        else:
            return wcb.say("Key '%s' does not exist." % k)
    
    if event['command'] == 'del':
        k = event['command_args']
        if k in wcb.state:
            ov = wcb.state[k]
            del wcb.state[k]
            wcb.save_bot_configuration()
            return wcb.say("Key '%s' was removed! Value was: '%s'" % (k, ov))
        else:
            return wcb.say("Key '%s' does not exist." % k)
    
    if event['command'] == 'list':
        keys = ", ".join(wcb.state.keys())
        return wcb.say("The following keys are in state: %s" % keys)
