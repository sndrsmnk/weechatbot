from datetime import datetime
import requests
import json
import re

def config(wcb):
    return {
        'commands': ['hassver', 'haver'],
        'permissions': ['user'],
        'events': [],
        'help': "Fetches latest HomeAssistant release info."
    }


def run(wcb, event):
    # Only run in a specific channel :)
    if event['channel'] not in ['#nlhomeautomation', '#fdi-status']:
        return wcb.signal_cont

    req = requests.get("https://www.home-assistant.io/version.json")
    jsontxt = req.text
    try:
        obj = json.loads(jsontxt)
    except Exception as e:
        wcb.say("Parsing content failed: %s" % e)
        return wcb.signal_cont
    release_date_obj = datetime.fromisoformat(obj['release_date'])
    
    wcb.say(f"Latest Home Assistant version is {obj['current_version']} released {release_date_obj.strftime('%Y-%m-%d')}, see https://github.com/home-assistant/core/releases/tag/{obj['current_version']} !")

    # Update the topic for the channel!
    infolist = wcb.weechat.infolist_get('irc_channel', '', event['server'])
    while wcb.weechat.infolist_next(infolist):
        channel_name = wcb.weechat.infolist_string(infolist, 'name')
        if channel_name != event['channel']:
            continue
        modes = wcb.weechat.infolist_string(infolist, 'modes')
        topic = wcb.weechat.infolist_string(infolist, 'topic')
    wcb.weechat.infolist_free(infolist)
    if not event['bot_is_op'] and 't' in modes:
            wcb.mlog("Would update topic, but bot is not op and channel mode is +t.")
            return

    topicParts = []
    if topic != '':
        topicParts = topic.split('|')
    newTopicParts = []
    setTopic = 1
    found = 0
    for var in topicParts:
        topicPart = var.lstrip().rstrip()
        if topicPart == '':
            setTopic = 1
            continue

        newPart = topicPart
        if robj := re.match(r'^\s*LastHass: ([^\s]+) released', topicPart):
            found = 1
            if obj['current_version'] == robj.group(1):
                setTopic = 0
            else:
                newPart = f"LastHass: {obj['current_version']} released {release_date_obj.strftime('%Y-%m-%d')}"
        newTopicParts.append(newPart)

    if not found:
        newTopicParts.append(f"LastHass: {obj['current_version']} released {release_date_obj.strftime('%Y-%m-%d')}")

    if setTopic:
        newTopic = ' | '.join(newTopicParts)
        wcb.weechat.command(event['weechat_buffer'], '/topic ' + newTopic)

    return wcb.signal_stop
