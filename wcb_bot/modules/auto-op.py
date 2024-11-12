def config(wcb):
    return {
        'events': ['irc_in2_JOIN'],
        'commands': ['op', 'voice'],
        'permissions': ['auto-op', 'auto-voice'],
        'help': "Test"
    }

def run(wcb, event):
    if not event['bot_is_op']:
        return wcb.mlog("Bot is not opped on channel '%s'. Can't auto-op/auto-voice." % event['channel'])

    if not wcb.perms('owner') and (wcb.perms('dno') or wcb.perms('dnv')):
        return

    tgtNick = event['nick']
    if event['command_args']:
        cmd = event['command']
        tgtNick = event['command_args'].split(' ')[0]
    else:
        if wcb.perms('auto-op'):
            cmd = 'op'
        elif wcb.perms('auto-voice'):
            cmd = 'voice'

    log = f"Gave {cmd} to '{tgtNick}' on channel '{event['channel']}'"
    if event['command_args']:
        log += f" on behalf of '{event['nick']}'"
    log += "."
    wcb.mlog(log)

    wcb.weechat.command(event['weechat_buffer'], f"/{cmd} {tgtNick}")
    return wcb.weechat.WEECHAT_RC_OK

