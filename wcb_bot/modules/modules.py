def config():
    return {
        'events': [],
        'commands': ['load', 'reload', 'unload', 'avail'],
        'permissions': ['modules'],
        'help': "Provides load, reload, unload functionality for modules",
    }


def run(wcb, event):
    if event['command'] == 'avail':
        mlist = ", ".join(sorted(wcb.modules.keys()))
        wcb.say("Modules loaded: %s" % mlist)
        return wcb.weechat.WEECHAT_RC_OK


    # Commands below require param to be set.        
    if event['command_args'] == '':
        wcb.reply("this command requires at least one argument (module name)")
        return wcb.weechat.WEECHAT_RC_OK

    if event['command'] == 'load' or event['command'] == 'reload':
        res = wcb.load_module(event['command_args'])
        wcb.say(res)
        return wcb.weechat.WEECHAT_RC_OK

    if event['command'] == 'unload':
        wcb.unload_module(event['command_args'])
        wcb.say("Unloaded module '%s'" % event['command_args'])
        return wcb.weechat.WEECHAT_RC_OK

    if event['command'] == 'avail':
        rtxt = 'Modules loaded: %s' % (', '.join(sorted(self.modules)))
        wcb.say(rtxt)
        return wcb.weechat.WEECHAT_RC_OK

    return wcb.weechat.WEECHAT_RC_ERROR
