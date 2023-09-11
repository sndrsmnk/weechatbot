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
    mac_input = mac_input.replace('-', '').replace(':', '')
    if len(mac_input) < 6:
        raise Exception("need at least 3 octets")

    mac_input = mac_input[:6]

    with open('/usr/share/nmap/nmap-mac-prefixes', 'r') as f :
        for line in f:
          if line.startswith(mac_input):
            return(line[7:-1])
            break

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

if __name__ == '__main__':
    import sys
    print(OUILookup(sys.argv[1]))
