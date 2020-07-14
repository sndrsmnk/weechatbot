def config():
    return {
        'events': [],
        'commands': ['botnick'],
        'permissions': ['botnick'],
        'help': "Renames the bot on the current network"
    }


def run(wcb, event):
    newnick = event['command_args']

    if not newnick or newnick == '':
        return wcb.reply("please do specify a nick name!")
    
    wcb.weechat.command(event['weechat_buffer'], '/nick ' + newnick)
    wcb.weechat.command(event['weechat_buffer'], '/set irc.server.%s.nicks %s' % (event['server'], newnick))
    wcb.weechat.command(event['weechat_buffer'], '/save')
    return wcb.weechat.WEECHAT_RC_OK
