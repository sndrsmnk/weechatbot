import re
import time


def config(wcb):
    if not 'reoplist' in wcb.state:
        wcb.state['reoplist'] = {}
    if not 'reoplist_interval' in wcb.state:
        wcb.state['reoplist_interval'] = 86400

    return {
        'events': ['irc_in2_344', 'irc_in2_345', 'timer_signal'],
        'commands': ['reoplist'],
        'permissions': ['owner'],
        'help': "When '!reoplist on' (off is default), bot will check for and maintain an IRCNet Reop-list entry on the channel periodically.",
    }


def timer_event(wcb, event):
    """ This function can make no assumption on the event data. It is empty for the most part. """
    """ All message routing, if any, must be done with manual lookups of buffers and raw commands. """
    for tag in list(wcb.state['reoplist'].keys()):
        cmd_output_buffer = wcb.weechat.buffer_search('irc', '(?i)'+tag) # (?i) case insensitive
        if not cmd_output_buffer:
            wcb.mlog(f"Can't find reoplist channel '{tag}'. Dropping.")
            del wcb.state['reoplist'][tag]
            wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])
            continue

        now = int(time.time())
        last_upd = int(wcb.state['reoplist'][tag]['last_check'])
        if now - last_upd > wcb.state['reoplist_interval']:
            _, *channel = tag.split('.')
            channel = '.'.join(channel)
            wcb.weechat.command(cmd_output_buffer, f"/mode {channel} +R")
            wcb.state['reoplist'][tag]['last_check'] = now
            wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])

    return wcb.weechat.WEECHAT_RC_OK


def reoplist_item_event(wcb, event, tag, bot_plus_r_nickmask):
    plus_r_nickmask = event['text']
    if plus_r_nickmask == bot_plus_r_nickmask:
        wcb.state['reoplist'][tag]['found_self'] = 1
    return


def reoplist_list_end_event(wcb, event, tag, bot_plus_r_nickmask):
    # If at the end of the reop list we haven't found our bot_plus_r_nickmask,
    # look up buffer and issue +R mode command.
    if not wcb.state['reoplist'][tag]['found_self']:
        obuffer = False
        servers = wcb.weechat.infolist_get("irc_server", "", "")
        while wcb.weechat.infolist_next(servers):
            this_server = wcb.weechat.infolist_string(servers, 'name')
            if event['server'] != this_server:
                continue
            obuffer = wcb.weechat.infolist_pointer(servers, 'buffer')
        wcb.weechat.infolist_free(servers)
        if not obuffer:
            wcb.mlog("Can't find output buffer for +R event.")
            self.debug_event()
            return wcb.weechat.WEECHAT_RC_OK
        wcb.mlog(f"Sent '/mode {event['channel']} +R {bot_plus_r_nickmask}' on server {event['server']}")
        wcb.weechat.command(obuffer, f"/mode {event['channel']} +R {bot_plus_r_nickmask}")

    # Reset state for next run:
    wcb.state['reoplist'][tag]['found_self'] = 0
    return


def run(wcb, event):
    if event['signal'] == 'timer_signal':
        return timer_event(wcb, event)

    # AFAIK only IRCnet supports +R reop-list
    if event['server'] != 'ircnet':
        return wcb.weechat.WEECHAT_RC_OK

    if not event['bot_is_op']:
        wcb.mlog(f"Reoplist was activated on {event['server']}.{event['channel']} but bot is not op :(")
        return wcb.weechat.WEECHAT_RC_OK

    tag = event['server'] + '.' + event['channel']
    bot_plus_r_nickmask = event['bot_nick'] + '*!*' + event['bot_hostmask']
    bot_plus_r_nickmask = re.sub(r'!.*@', '!*@', bot_plus_r_nickmask)

    if event['signal'] == 'irc_in2_344':
        reoplist_item_event(wcb, event, tag, bot_plus_r_nickmask)
        return wcb.weechat.WEECHAT_RC_OK

    if event['signal'] == 'irc_in2_345':
        reoplist_list_end_event(wcb, event, tag, bot_plus_r_nickmask)
        return wcb.weechat.WEECHAT_RC_OK

    if event['command'] == 'reoplist':
        arg = event['command_args']

        if arg == '':
            if tag in wcb.state['reoplist']:
                wcb.say("is active.")
            else:
                wcb.say("is inactive.")
            return wcb.weechat.WEECHAT_RC_OK

        elif re.match(r'^\s*[Oo][Nn]\s*$', arg):
            wcb.state['reoplist'][tag] = {'last_check': 0, 'found_self': 0}
            wcb.save_obj_as_json(wcb.state, wcb.state['bot_config'])
            wcb.say("ok.")
            return wcb.weechat.WEECHAT_RC_OK
        
        elif re.match(r'^\s*[Oo][Ff][Ff]\s*$', arg):
            if tag in wcb.state['reoplist']:
                del wcb.state['reoplist'][tag]
            wcb.say("ok.")
            return wcb.weechat.WEECHAT_RC_OK
        
        else:
            return wcb.say("Expecting 'on' or 'off', not '%s'" % arg)
