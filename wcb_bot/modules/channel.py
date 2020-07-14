def config():
    return {
        'events': ['irc_in2_INVITE'],
        'commands': ['join', 'part'],
        'permissions': ['join', 'part'],
        'help': "Responds to invites, join and part commands."
    }


def run(wcb, event):
    if event['signal'] == 'irc_in2_INVITE':
        chan = event['text']
        wcb.mlog("Joining channel '%s' on invite from '%s'" % (chan, event['host']))
        wcb.weechat.command(event['weechat_buffer'], '/join -server %s %s' % (event['server'], chan))

    if event['command'] == 'join':
        chan = event['command_args']
        wcb.mlog("Joining channel '%s' on command from '%s'" % (chan, event['host']))
        wcb.weechat.command(event['weechat_buffer'], '/join -server %s %s' % (event['server'], chan))

    if event['command'] == 'part':
        chan = event['command_args']
        if not chan or chan == '':
            chan = event['channel']
        wcb.mlog("Leaving channel '%s' on command from '%s'" % (chan, event['host']))
        wcb.weechat.command(event['weechat_buffer'], '/part %s' % (chan))
   
    # See if autojoin.py by 'xt' is loaded, if so, deal with that.
    autojoin_enable = False
    infolist = wcb.weechat.infolist_get('python_script', '', '*')
    while wcb.weechat.infolist_next(infolist):
        name = wcb.weechat.infolist_string(infolist, 'name')
        author = wcb.weechat.infolist_string(infolist, 'author')
        if name == 'autojoin' and 'xt@bash.no' in author:
            autojoin_enable = True
            break
    if autojoin_enable:
        wcb.mlog("Found autojoin script loaded. Saving autojoin state.")
        wcb.weechat.command(event['weechat_buffer'], '/autojoin --run')
