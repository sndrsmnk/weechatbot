def config(wcb):
    return {
        'events': ['irc_in2_JOIN'],
        'commands': ['op', 'voice'],
        'permissions': ['auto-op', 'auto-voice'],
        'help': "Test"
    }

def auto_op_timer_event(wcb, event):
    return wcb.WEECHAT_RC_OK

def run(wcb, event):
    if event['signal'] == 'timer_signal':
        return auto_op_timer_event(wcb, event)

    if not event['bot_is_op']:
        return

    if not wcb.perms('owner') and (wcb.perms('dno') or wcb.perms('dnv')):
        return

    tgtNick = event['nick']
    prefix = ''

    if event['command_args']:
        cmd = event['command']
        tgtNick = event['command_args'].split(' ')[0]
        if cmd == 'op':
            prefix = '@'
        elif cmd == 'voice':
            prefix = '+'
    else:
        if wcb.perms('auto-op'):
            cmd = 'op'
            prefix = '@'
        elif wcb.perms('auto-voice'):
            cmd = 'voice'
            prefix = '+'

    # Figure out of nick already has ops/voice.
    infolist = wcb.weechat.infolist_get('irc_nick', '', '%s,%s' % (event['server'], event['channel']))
    while wcb.weechat.infolist_next(infolist):
        nick = wcb.weechat.infolist_string(infolist, 'name')
        if nick != tgtNick:
            continue
        if prefix in wcb.weechat.infolist_string(infolist, 'prefix'):
            wcb.mlog(f"Nick '{tgtNick}' on channel '{event['channel']}' already has {cmd}")
            wcb.weechat.infolist_free(infolist)
            return wcb.weechat.WEECHAT_RC_OK

    wcb.weechat.infolist_free(infolist)

    log = f"Gave {cmd} to '{tgtNick}' on channel '{event['channel']}'"
    if event['command_args']:
        log += f" on behalf of '{event['nick']}'"
    log += "."
    wcb.mlog(log)

    wcb.weechat.command(event['weechat_buffer'], f"/{cmd} {tgtNick}")
    return wcb.weechat.WEECHAT_RC_OK

