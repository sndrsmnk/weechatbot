import requests
import json
import random
import binascii
import time
import re

from collections import namedtuple

# TODO: OUIs that are not 24 bits
# TODO: wwn?

def config(wcb):
    return {
        'events': [],
        'commands': ['mac', 'oui'],
        'permissions': ['user'],
        'help': "Look up vendors for mac addresses using macvendors.com"
    }

def OUItrySpecial(mac, extra):
    arpsponges = {
        'C6174426E887': 'AMSIX',
        '001B215F2E35': 'LINX',
        '0ABFA1100000': 'DECIX'
    }

    ix = arpsponges.get(mac)

    if ix:
        extra.extend(['ARP sponge', ix])
        return

    if mac.startswith('525400'):  # 525400 is in the nmap MAC database too, but we look for 505400 there if the input is 525400
        extra.append('qemu/kvm?')
        return

    try:
        bmac = binascii.a2b_hex(mac)
    except:
        return []

    if len(bmac) == 6:
        if mac.startswith('00005E'):  # IANA
            # https://www.iana.org/assignments/ethernet-numbers/ethernet-numbers.xhtml#ethernet-numbers-1
            if bmac[3] == 0:
                if bmac[4] == 1:   # 00-00-5E-00-01-xx
                    extra.append('IPv4 VRRP')
                elif bmac[4] == 2:
                    extra.append('IPv6 VRRP')
                elif bmac[4] == 0x53:
                    extra.append('Documentation range')
                else:
                    return

                extra.append('id %d' % (bmac[5],))
        elif mac.startswith('01005E'):  # v4 multicast group
            if bmac[3] <= 0x7f:
                addr = '224.%d.%d.%d' % (bmac[3], bmac[4], bmac[5])
                extra.append("IPv4 "+addr+"?")
            elif bmac[3] <= 0x8f:
                extra.append("MPLS [RFC5332]")
        elif mac.startswith('3333'):  # v6 multicast
            extra.append("IPv6 multicast for xx::%x%02x:%x%02x" % (bmac[2], bmac[3], bmac[4], bmac[5]))


def macvendorsLookup(wcb, mac_input):
    res = requests.get("https://api.macvendors.com/" + mac_input)

    restxt = res.text
    if restxt.startswith('{"'):
        obj = json.loads(restxt)
        if 'errors' in obj and 'detail' in obj['errors']:
            detail = obj['errors']['detail']
            if detail == "Not Found":
                return detail
            else:
                raise Exception(detail)
        else:
            raise Exception("Got JSON that i cant deal with yet: '%s'" % restxt)

    return restxt

def nmapLookup(wcb, mac_input):
    res = ''

    with open('/usr/share/nmap/nmap-mac-prefixes', 'r') as f :
        for line in f:
          if line.startswith(mac_input):
            res = line[7:-1]
            break

    if not res:
        res = 'unknown'

    return res

def actualOUILookup(wcb, mac_input):
    backend = wcb.state.get('oui_backend', 'macvendors')

    if backend == 'macvendors':
        return macvendorsLookup(wcb, mac_input)
    elif backend == 'nmap':
        return nmapLookup(wcb, mac_input)
    else:
        return 'please set oui_backend to "macvendors" or "nmap"'

def OUILookup(wcb, mac_input):
    mac_input = mac_input.upper()
    mac_input = mac_input.replace('-', ':')
    mac_input = re.sub('[^A-F0-9:]', '', mac_input)

    octets = mac_input.split(':')

    # prepend zero to octets that are only one nibble long
    for i in range(len(octets)):
        if len(octets[i]) == 1:
            octets[i] = '0' + octets[i]

    mac_input = ''.join(octets)

    mac_input = mac_input.replace('-', '').replace(':', '').upper()
    if len(mac_input) < 6:
        raise Exception("need at least 3 octets (got input %s)" % (mac_input,))

    extra = []
    OUItrySpecial(mac_input, extra)  # this may append to `extra`

    mac_input = mac_input[:6]

    octet0 = int(mac_input[0:2], 16)

    if octet0 & 1:
        extra.append('multicast')

    if octet0 & 2:
        extra.append('admindefined')

    mac_input = '%02X%s' % (octet0 & (0xff-3), mac_input[2:])

    # TODO: make this filename configurable
    # TODO: write down, perhaps right here in this comment, how to make a fresh file in the same format
    res = actualOUILookup(wcb, mac_input)

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
        restxt = OUILookup(wcb, mac_input)
    except Exception as err:
        return wcb.reply("API fail: %s" % err)

    # API returns vendor name as a single string, or JSON on errors.

    return wcb.reply(restxt)

# $ pytest ./oui.py
def test_lookup():
    for backend in ['nmap', 'macvendors']:
        wcb = namedtuple('state', ['state'])(dict(oui_backend=backend))
        for oui, res in [
            ('009069', ['Juniper Networks']),
            ('00:90:69', ['Juniper Networks']),
            ('00-90-69', ['Juniper Networks']),
            ('0090.69', ['Juniper Networks']),
            ('0:90:69', ['Juniper Networks']),
            ('0-90:69', ['Juniper Networks']),
            ('019069', ['Juniper Networks (multicast)']),
            ('00005E-00-02-01', ['Icann, Iana Department (IPv6 VRRP, id 1)', 'ICANN, IANA Department (IPv6 VRRP, id 1)']),
            ('0000:5E:00-01-55', ['Icann, Iana Department (IPv4 VRRP, id 85)', 'ICANN, IANA Department (IPv4 VRRP, id 85)']),
            ('01005E-40-41-42', ['Icann, Iana Department (IPv4 224.64.65.66?, multicast)', 'ICANN, IANA Department (IPv4 224.64.65.66?, multicast)']),
            ('333340414243', ['unknown (IPv6 multicast for xx::4041:4243, multicast, admindefined)', 'Not Found (IPv6 multicast for xx::4041:4243, multicast, admindefined)']),
            ('3c:e1:a1:4c:dc:ac', ['Universal Global Scientific Industrial', 'Universal Global Scientific Industrial Co., Ltd.']),
            ('525400', ['unknown (qemu/kvm?, admindefined)', 'Not Found (qemu/kvm?, admindefined)']),
          ]:
          assert OUILookup(wcb, oui) in res, backend
          if backend == 'macvendors':
            time.sleep(2)

# $ python3 ./oui.py macvendors 3c:e1:a1:4c:dc:ac
if __name__ == '__main__':
    import sys
    wcb = namedtuple('state', ['state'])(dict(oui_backend=sys.argv[1]))
    print(OUILookup(wcb, sys.argv[2]))
