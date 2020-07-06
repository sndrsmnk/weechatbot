def config():
    return {
        'events': [],
        'commands': ['test'],
        'permissions': [],
        'help': "Test"
    }


def run(wcb, event):

    infolist = wcb.weechat.infolist_get('irc_nick', '', '%s,%s' % (event['server'], event['channel']))
    while wcb.weechat.infolist_next(infolist):
        nick = wcb.weechat.infolist_string(infolist, 'name')

        fields = wcb.weechat.infolist_fields(infolist).split(",")
        for field in fields:
            type, key = field.split(":")
            if type == 's' and key == 'prefix':
                val = wcb.weechat.infolist_string(infolist, key)
                wcb.say(key)
                wcb.say(val)
        wcb.say("----")

#       host = wcb.weechat.infolist_string(infolist, 'host')
#   msg = wcb.weechat.buffer_get_string(event['weechat_buffer'], 'localvar_nick')

#   wcb.say(msg)
#   wcb.mlog(msg)

    return wcb.weechat.WEECHAT_RC_OK
