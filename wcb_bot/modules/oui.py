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

    octet0 = int(mac_input[0:2], 16)

    extra = []

    if octet0 & 1:
        extra.append('multicast')

    if octet0 & 2:
        extra.append('admindefined')

    mac_input = '%02x%s' % (octet0 & (0xff-3), mac_input[2:])

    res = ''

    with open('/usr/share/nmap/nmap-mac-prefixes', 'r') as f :
        for line in f:
          if line.startswith(mac_input):
            res = line[7:-1]
            break

    if not res:
        res = 'unknown'

    if extra:
        res = '%s (%s)' % (res, ', '.join(extra))

    return res

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

def test_lookup():
    for oui, res in [
        ('009069', 'Juniper Networks'),
        ('019069', 'Juniper Networks (multicast)'),
      ]:
      assert OUILookup(oui) == res

if __name__ == '__main__':
    import sys
    print(OUILookup(sys.argv[1]))
