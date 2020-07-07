def config():
    return {
        'events': ['irc_in2_JOIN'],
        'commands': ['op', 'voice'],
        'permissions': ['auto-op', 'auto-voice'],
        'help': "Test"
    }


def run(wcb, event):
    if not event['bot_is_op']:
        wcb.mlog("Bot is not opped on channel '%s'. Can't auto-op/auto-voice." % event['channel'])
        return wcb.weechat.WEECHAT_RC_OK

    if not event['user_info']:
        wcb.mlog("User '%s' not recognized." % event['host'])
        return wcb.weechat.WEECHAT_RC_OK
    
    if 'auto-op' in event['user_info']['permissions']:
        wcb.say('XXX auto-op')
        return wcb.weechat.WEECHAT_RC_OK

    wcb.say("Welkom")
    return wcb.weechat.WEECHAT_RC_OK
