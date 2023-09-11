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

def OUILookup(mac_input):
    res = requests.get("https://api.macvendors.com/" + mac_input)

    restxt = res.text
    if restxt.startswith('{"'):
        obj = json.loads(restxt)
        if 'errors' in obj and 'detail' in obj['errors']:
            detail = obj['errors']['detail']
            if detail == "Not Found":
                raise KeyError(detail)
            else:
                raise Exception(detail)
        else:
            raise Exception("Got JSON that i cant deal with yet: '%s'" % restxt)

    return restxt


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
        restxt = OUILookup(mac_input)
    except KeyError:
        return wcb.reply("Not Found");
    except Exception as err:
        return wcb.reply("API fail: %s" % err)

    # API returns vendor name as a single string, or JSON on errors.

    return wcb.reply(restxt)
