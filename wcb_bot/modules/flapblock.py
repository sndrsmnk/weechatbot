import time

def config(wcb):
    if 'flapblock' not in wcb.state:
        wcb.state['flapblock'] = {}

    return {
        'events': ['irc_in2_JOIN', 'irc_in2_QUIT', 'irc_in2_PART', 'irc_in2_PRIVMSG'],
        'commands': ['flapblock'],
        'permissions': [],
        'help': "Kickbans users that join/part/quit in rapid succession without saying anything"
    }

def handle_flapblock_cmd(wcb, event):
    if not wcb.perms('owner'):
        return
    wcb.say("Yes.")
    return wcb.weechat.WEECHAT_RC_OK

def run(wcb, event):
    if event['command'] == 'flapblock':
        return handle_flapblock_cmd(wcb, event)
    
    uniq_src = event['target_channel'] + '.' + event['nickmask']

    if event['signal'] == 'irc_in2_PRIVMSG':
        if uniq_src in wcb.state['flapblock']:
            wcb.state['flapblock'].pop(uniq_src, '')
        return wcb.weechat.WEECHAT_RC_OK

    if event['signal'] == 'irc_in2_JOIN' or event['signal'] == 'irc_in2_PART' or event['signal'] == 'irc_in2_QUIT':
        # clean up state
        flapblock_keys = wcb.state['flapblock'].copy()
        for entry in flapblock_keys:
            age = int(time.time()) - wcb.state['flapblock'][entry]['last']
            if age >= 60: # XXX
                wcb.state['flapblock'].pop(entry, '')

        # new entry
        if uniq_src not in wcb.state['flapblock']:
            wcb.state['flapblock'][uniq_src] = {
                'score': 1,
                'last': int(time.time())
            }
            return wcb.weechat.WEECHAT_RC_OK

        # scoring entry
        wcb.state['flapblock'][uniq_src]['score'] += 1
        wcb.state['flapblock'][uniq_src]['last'] = int(time.time())

        # threshold
        if wcb.state['flapblock'][uniq_src]['score'] > 3: # XXX
            # if it happened, event[] holds the correct info to ban and kick
            wcb.weechat.command(event['weechat_buffer'], '/ban ' + event['nickmask'])
            wcb.weechat.command(event['weechat_buffer'], '/kick ' + event['nick'] + ' Fix your connection. You are flapping. Timeout!')
            wcb.private("You have been timed out from " + event['channel'] + " for excessive flapping. Your connection seems unstable.")

        if wcb.state['flapblock'][uniq_src]['score'] == 3: # XXX
            if event['signal'] == 'irc_in2_JOIN':
                wcb.reply("say something to prevent being timed out for flapping!")
            
    return wcb.weechat.WEECHAT_RC_OK
