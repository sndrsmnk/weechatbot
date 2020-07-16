def config(wcb):
    return {
        'events': [],
        'commands': ['help'],
        'permissions': ['user'],
        'help': "Shows this help text for modules."
    }


def run(wcb, event):
    module = event['command_args']
    if not module in wcb.modules:
        return wcb.reply("a module named '%s' was not found loaded! Try the 'avail' command!" % module)
    helptxt = wcb.modules[module]['help']
    helpcmds = ", ".join(wcb.modules[module]['commands'])
    helpperm = ", ".join(wcb.modules[module]['permissions'])

    wcb.say("%s" % (helptxt))
    wcb.say("Provides commands: %s" % (helpcmds))
    wcb.say("Needs permissions: %s" % (helpperm))
    return
