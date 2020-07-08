def config():
    return {
        'events': [],
        'commands': ['test2'],
        'permissions': ['user'],
        'help': "Test2"
    }


def run(wcb, event):
    a = 100 / 0
    return wcb.weechat.WEECHAT_RC_OK
