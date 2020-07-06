def config():
    return {
        'events': [],
        'commands': ['owner'],
        'permissions': [],
        'help': "Helps with claiming bot ownership when the bot has not been claimed before\nUsage: !owner <bot_uniqueid>",
    }


def run(wcb, event):
    if wcb.state['bot_ownermask'] != '' and wcb.state['bot_ownermask'] != event['host']:
        wcb.reply("no you're not.")
        return wcb.weechat.WEECHAT_RC_OK

    if wcb.state['bot_ownermask'] != '' and wcb.state['bot_ownermask'] == event['host']:
        wcb.reply("yes you are!")
        return wcb.weechat.WEECHAT_RC_OK

    if event['command_args'] != wcb.state['bot_uniqueid']:
        wcb.reply("sorry, that is not the correct id to win my heart.")
        return wcb.weechat.WEECHAT_RC_OK

    wcb.say("Hi! You are now my owner!")
    wcb.state['bot_ownermask'] = event['host']
    wcb.load_all_modules()
    wcb.save_bot_configuration()
    return wcb.weechat.WEECHAT_RC_OK
