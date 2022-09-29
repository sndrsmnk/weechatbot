def config(wcb):
    return {
        'events': [],
        'commands': ['v', 'version'],
        'permissions': [],
        'help': "Shows info on the bot"
    }

def run(wcb, event):
    return wcb.say("WeeChatBot - https://github.com/sndrsmnk/weechatbot/")
