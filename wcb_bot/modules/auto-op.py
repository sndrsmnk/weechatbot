def config(wcb):
    return {
        'events': ['irc_in2_JOIN'],
        'commands': ['op', 'voice'],
        'permissions': ['auto-op', 'auto-voice'],
        'help': "Test"
    }


def run(wcb, event):
    if not event['bot_is_op']:
        return wcb.mlog("Bot is not opped on channel '%s'. Can't auto-op/auto-voice." % event['channel'])

    tgtNick = event['nick']
    if event['command_args']:
        tgtNick = event['command_args'].split(' ')[0]

    log = "Gave ops to '%s' on channel '%s'" % (tgtNick, event['channel'])
    if event['command_args']:
        log += " on behalf of '%s'" % event['nick']
    log += "."
    wcb.mlog(log)
    wcb.weechat.command(event['weechat_buffer'], '/op ' + tgtNick)
    return wcb.weechat.WEECHAT_RC_OK
