def config():
    return {
        'events': [ ],
        'commands': ['udp-reopen'],
        'permissions': ['udp-reopen'],
        'help': "Restart / reopens the UDP-listener after you made changes to the settings."
    }


def run(wcb, event):
    wcb.setup_udp_listener()
    return wcb.say("UDP-listener re-opened.")
