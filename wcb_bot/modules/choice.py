import random


def config(wcb):
    return {
        'events': [],
        'commands': ['choose', 'choice'],
        'permissions': ['user'],
        'help': "Helps decide between a number of evils.  !choice a b c d e"
    }


def run(wcb, event):
    valstr = wcb.re.sub(r'\s+', ' ', event['command_args'])
    valarr = valstr.split(' ')
    val = random.choice(valarr)
    if not val:
        return wcb.reply("please provide your options!")
    return wcb.reply(val)
