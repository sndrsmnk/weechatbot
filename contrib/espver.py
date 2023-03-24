from datetime import datetime
import requests
import json
import re

def config(wcb):
    return {
        'commands': ['espver', 'esphomever'],
        'permissions': ['user'],
        'events': [],
        'help': "Fetches latest ESPhome release info."
    }


def run(wcb, event):
    # Only run in a specific channel :)
    if event['channel'] not in ['#nlhomeautomation', '#fdi-status']:
        return wcb.signal_cont

    showdev = False
    if event['command_args'] in ['dev', 'devel', 'development']:
        showdev = True

    req = requests.get("https://api.github.com/repos/esphome/esphome/releases")
    jsontxt = req.text
    try:
        obj = json.loads(jsontxt)
    except Exception as e:
        wcb.say("Parsing content failed: %s" % e)
        return wcb.signal_cont
 
    dev = ""
    rls = ""
    for elem in obj:
        if not dev and elem['target_commitish'] == 'dev':
            dev = "ESPHome latest development version %s, released %s, see %s" % (elem['name'], elem['published_at'], elem['html_url'])
        if not rls and elem['target_commitish'] == 'release':
            rls = "ESPHome latest release version %s, released %s, see %s" % (elem['name'], elem['published_at'], elem['html_url'])

    if showdev:
        wcb.say(dev)
        return wcb.signal_stop

    wcb.say(rls)
    return wcb.signal_stop
