import requests
import json

def config(wcb):
    return {
        'events': [],
        'commands': ['kink'],
        'permissions': ['user'],
        'help': "K!NK Now Playing"
    }


def run(wcb, event):
    # Only run in a specific channel :)
    if event['channel'] not in ['#cistron', '#fdi-status']:
        return wcb.signal_cont

    try:
        res = requests.get("https://api.kink.nl/static/now-playing.json")
    except Exception as err:
        return wcb.reply("i failed: '%s'" % err)

    obj = json.loads(res.text)
    try:
        cur = obj['playing']
    except Exception as err:
        return wcb.reply("i failed: '%s'" % err)
    return wcb.reply("ꓘINK is currently playing: '%s'" % cur)
