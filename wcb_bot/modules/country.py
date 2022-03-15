import random
from iso3166 import countries


def config(wcb):
    return {
        'events': [],
        'commands': ['cc', 'country'],
        'permissions': ['user'],
        'help': "Tries to decode two- and three letter ISO3166 country codes"
    }


def run(wcb, event):
    cc = event['command_args']
    ccobj = countries.get(cc)
    if not ccobj:
        wcb.say(f"It doesn't look like '{cc}' is a country code or number.")
        return wcb.signal_stop

    wcb.say(f"Country code {ccobj.alpha2} ({ccobj.alpha3}/{ccobj.numeric}) is {ccobj.name}.")
    return wcb.signal_stop
