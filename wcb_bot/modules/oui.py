import requests
import json
import random


def config(wcb):
    return {
        'events': [],
        'commands': ['mac', 'oui'],
        'permissions': ['user'],
        'help': "Look up vendors for mac addresses using macvendors.com"
    }


def run(wcb, event):
    mac_input = event['command_args']
    if not mac_input or mac_input == '':
        if event['command'] == "oui":
            repondre = [
                "Ah putain, Non!",
                "... du Paturain!",
                "... Ah, l'amour!",
                "Je ne sais pas ce que vous voulez dire!"
            ]
            wcb.say(random.choice(repondre))
        return wcb.reply("Usage: ![mac|oui] <macaddress>")

    try:
        res = requests.get("https://api.macvendors.com/" + mac_input)
    except Exception as err:
        return wcb.reply("API fail: %s" % err)

    # API returns vendor name as a single string, or JSON on errors.
    restxt = res.text
    if restxt.startswith('{"'):
        obj = json.loads(restxt)
        if 'errors' in obj and 'detail' in obj['errors']:
            return wcb.reply(obj['errors']['detail'])
        else:
            return wcb.reply("Got JSON that i cant deal with yet: '%s'" % restxt)

    return wcb.reply(restxt)
