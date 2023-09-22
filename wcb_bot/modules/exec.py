#
# This module is an example on how to run a background process and deal with its
# output through a callback routine. The callback routine aparently can be called
# multiple times, possibly depending on how big the stdout/err output from your
# process is.
#
# Always be mindful and wary when executing commands on behalf of the public! :-)
#

def config(wcb):
    return {
        'events': ['hook_process_callback'],
        'commands': ['exec'],
        'permissions': ['owner'],
        'help': "Example of doing blocking stuff in WeeChatBot. Runs only for owner."
    }


def exec_cb(wcb, event):
    wcb.say("Command '%s'" % event['process'])
    wcb.say("stdout: %s" % event['process_stdout'])
    # process_rc
    # process_stderr
    return wcb.weechat.WEECHAT_RC_OK


def run(wcb, event):
    if event['signal'] == 'hook_process_callback':
        return exec_cb(wcb, event)
    wcb.hook_process("/home/sanders/wcb_exec.sh", 5000)
