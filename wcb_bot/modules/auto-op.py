def config(wcb):
    return {
        'events': ['timer_signal', 'irc_in2_JOIN'],
        'commands': ['op', 'voice'],
        'permissions': ['auto-op', 'auto-voice'],
        'help': "Test"
    }


def _find_buffer_and_do(wcb, servername, channel, cmd):
    obuffer = False
    servers = wcb.weechat.infolist_get("irc_channel", "", f"{servername},{channel}")
    while wcb.weechat.infolist_next(servers):
        obuffer = wcb.weechat.infolist_pointer(servers, 'buffer')
    wcb.weechat.infolist_free(servers)
    if not obuffer:
        wcb.mlog(f"Auto-op could not find buffer for {servername}.{channel} '{cmd}'")
        return wcb.weechat.WEECHAT_RC_OK
    wcb.mlog(f"Auto-op ran {servername}.{channel} '{cmd}'")
    return wcb.weechat.command(obuffer, cmd)


def auto_op_timer_event(wcb, event):
    if 'auto-op-queue' not in wcb.state:
        return

    for servername in wcb.state['auto-op-queue']:
        for channel in wcb.state['auto-op-queue'][servername]:
            for operation in wcb.state['auto-op-queue'][servername][channel]:
                while True:
                    numNicks = len(wcb.state['auto-op-queue'][servername][channel][operation])

                    if numNicks == 0:
                        break

                    nicklist = ''
                    if numNicks >= 3:
                        nicklist = " ".join(wcb.state['auto-op-queue'][servername][channel][operation][:3])
                        del wcb.state['auto-op-queue'][servername][channel][operation][:3]
                    else:
                        nicklist = " ".join(wcb.state['auto-op-queue'][servername][channel][operation])
                        wcb.state['auto-op-queue'][servername][channel][operation] = []

                    cmd = f"/{operation} {nicklist}"
                    _find_buffer_and_do(wcb, servername, channel, cmd)
    return wcb.weechat.WEECHAT_RC_OK


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

    if not event['command_args']:
        # add to queue
        if 'auto-op-queue' not in wcb.state:
            wcb.state['auto-op-queue'] = {}
        if event['server'] not in wcb.state['auto-op-queue']:
            wcb.state['auto-op-queue'][event['server']] = {}
        if event['channel'] not in wcb.state['auto-op-queue'][event['server']]:
            wcb.state['auto-op-queue'][event['server']][event['channel']] = {}
        if cmd not in wcb.state['auto-op-queue'][event['server']][event['channel']]:
            wcb.state['auto-op-queue'][event['server']][event['channel']][cmd] = []
        if tgtNick not in wcb.state['auto-op-queue'][event['server']][event['channel']][cmd]:
            wcb.state['auto-op-queue'][event['server']][event['channel']][cmd].append(tgtNick)
        return wcb.weechat.WEECHAT_RC_OK

    log = f"Gave {cmd} to '{tgtNick}' on channel '{event['channel']}'"
    if event['command_args']:
        log += f" on behalf of '{event['nick']}'"
    log += "."
    wcb.mlog(log)

    wcb.weechat.command(event['weechat_buffer'], f"/{cmd} {tgtNick}")
    return wcb.weechat.WEECHAT_RC_OK

