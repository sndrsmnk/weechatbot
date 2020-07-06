def config():
    return {
        'events': [],
        'commands': ['test2'],
        'permissions': ['user'],
        'help': "Test2"
    }


def run(wcb, event):
    wcb.say("You must be a registered user!")
    return wcb.weechat.WEECHAT_RC_OK
