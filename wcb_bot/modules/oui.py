import requests
import json
import random
import binascii


def config(wcb):
    return {
        'events': [],
        'commands': ['mac', 'oui'],
        'permissions': ['user'],
        'help': "Look up vendors for mac addresses using macvendors.com"
    }

def OUItrySpecial(mac):
    if mac.startswith('525400'):  # 525400 is in the nmap MAC database too, but we look for 505400 there if the input is 525400
        return ['qemu/kvm?']

    try:
        mac = binascii.a2b_hex(mac)
    except:
        return []

    res = []

    if len(mac) == 6 and mac.startswith(b'\x00\x00\x5e'): # IANA
        # https://www.iana.org/assignments/ethernet-numbers/ethernet-numbers.xhtml#ethernet-numbers-1
        if mac[3] == 0:
            if mac[4] == 1:   # 00-00-5E-00-01-xx
                res.append('IPv4 VRRP')
            elif mac[4] == 2:
                res.append('IPv6 VRRP')
            else:
                return []

            res.append('id %d' % (mac[5],))

    return res


def OUILookup(mac_input):
    mac_input = mac_input.replace('-', '').replace(':', '').upper()
    if len(mac_input) < 6:
        raise Exception("need at least 3 octets")

    extra = OUItrySpecial(mac_input)

    mac_input = mac_input[:6]

    octet0 = int(mac_input[0:2], 16)

    if octet0 & 1:
        extra.append('multicast')

    if octet0 & 2:
        extra.append('admindefined')

    mac_input = '%02X%s' % (octet0 & (0xff-3), mac_input[2:])

    res = ''

    # TODO: make this filename configurable
    # TODO: write down, perhaps right here in this comment, how to make a fresh file in the same format
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

# $ pytest ./oui.py
def test_lookup():
    for oui, res in [
        ('009069', 'Juniper Networks'),
        ('019069', 'Juniper Networks (multicast)'),
        ('00005E-00-02-01', 'Icann, Iana Department (IPv6 VRRP, id 1)'),
        ('0000:5E:00-01-55', 'Icann, Iana Department (IPv4 VRRP, id 85)'),
        ('3c:e1:a1:4c:dc:ac', 'Universal Global Scientific Industrial'),
        ('525400', 'unknown (qemu/kvm?, admindefined)'),
      ]:
      assert OUILookup(oui) == res

# $ python3 ./oui.py 3c:e1:a1:4c:dc:ac
if __name__ == '__main__':
    import sys
    print(OUILookup(sys.argv[1]))
