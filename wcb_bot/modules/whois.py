def config():
    return {
        'events': [],
        'commands': ['whois'],
        'permissions': ['user'],
        'help': "Tells you who the bot thinks someone is."
    }


def run(wcb, event):
    tnick = event['command_args']

    if tnick == '':
        return wcb.reply("tell me who you're curious about.")

    if tnick == event['bot_nick']:
        return wcb.reply("i am the channel bot, %s" % event['bot_nick'])

    tuserhost = wcb.get_userhost_by_ircnick(tnick)
    if not tuserhost:
        return wcb.say("%s is not a party of this conversation." % tnick)
    else:
        wcb.say("%s is on channel %s as %s. " % (tnick, event['channel'], tuserhost))

    uibh = wcb.db_get_userinfo_by_ircnick(tnick)
    uibu = wcb.db_get_userinfo_by_username(tnick)
    if uibh:
        wcb.say("Recognized by userhost as user '%s'" % uibh['username'])
    elif not uibh and uibu:
        return wcb.say("Unrecognized user. But a user named '%s' exists. Perhaps merge? " % tnick)
    else:
        return wcb.say("Unrecognized user.")

    ret = "With "
    if uibh['permissions']['global']:
        ret += "global perms (%s) " % ", ".join(uibh['permissions']['global'])

        channel = event['channel']
        if channel in uibh['permissions']:
            ret += "and '%s' perms (%s)" % (event['channel'], ", ".join(uibh['permissions'][channel]))

    ret += "."
    wcb.say(ret)
    ret = ""

    ret = "Hostmasks: %s" % ", ".join(uibh['hostmasks'])
    return wcb.say(ret)
