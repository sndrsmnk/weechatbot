# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import random
import pprint
import shutil
import socket
import weechat
import inspect
import psycopg2
import tempfile
import traceback
import importlib.util
import psycopg2.extras
from datetime import datetime


def dlog(message):
    dlog_buffer = weechat.buffer_search('python', 'WeeChatBot')
    for ln in message.split("\n"):
        weechat.prnt(dlog_buffer, 'bot | ' + ln)
    return weechat.WEECHAT_RC_OK


class WeeChatBot:
    def __init__(self, weechat):
        self.weechat = weechat
        self.re = re
        self.buffer = self.weechat.buffer_new("WeeChatBot", "shim_wcb_handle_buffer_input", "", "", "")

        bot_base = os.environ['HOME'] + '/.weechat/python/wcb_bot'
        self.udp_socket_open = False
        self.modules = {}

        self.signal_cont = 0
        self.signal_stop = 1

        self.state = {
            'bot_base':          bot_base,
            'bot_modules':       '%s/modules' % bot_base,
            'bot_extra_modules': '%s/extra_modules' % bot_base,
            'bot_config':        '%s/wcb_config.json' % bot_base,
            'bot_alarms':        '%s/wcb_alarms.json' % bot_base,

            'bot_uniqueid':  ''.join(random.sample('abcdefghijklmnopqrstuvwxyzABCFEFGHIJKLMNOPQRSTUVWXYZ1234567890', 8)),
            'bot_ownermask': '',

            'bot_trigger_re': r'^[!\.]',

            # This regexp must return the command and the 'arguments' via (grou)(ping)
            'bot_command_re': r'([-a-zA-Z0-9]+)(?:\s(.*)|$)',

            # By default stuff like quotes, karma and infoitems are kept separate per channel.
            # '!set bot_shared_knowledge True' to disable and 'share the knowledge' between channels.
            'bot_shared_knowledge': False,

            'udp_listen_ip':   '::ffff:127.0.0.1',
            'udp_listen_port': 46664,
            'udp_listen_pass': 'WeeChatBot',

            'debug_udp':   False,
            'debug_event': False,

            'db_host': 'localhost',
            'db_port': '5432',
            'db_user': 'weechatbot',
            'db_pass': 'xyz',
            'db_name': 'weechatbot',

            'max_output_lines': 3,
        }

        for path in (self.state['bot_base'], self.state['bot_modules']):
            if not os.path.exists(path):
                try:
                    os.mkdir(path)
                    dlog("Created directory '%s'." % path)
                except Exception as err:
                    dlog("ERROR: Could not create directory '%s':" % path)
                    dlog("       %s" % err)
                    dlog("")

        if os.path.exists(self.state['bot_config']):
            self.state = self.load_obj_from_json(self.state['bot_config'])
        else:
            dlog("No configuration file was found. First startup?")

        if self.state['bot_ownermask'] != '':
            dlog("My owner is '%s'" % self.state['bot_ownermask'])
            self.load_all_modules()
        else:
            dlog("")
            dlog("My Unique ID is currently '%s'" % self.state['bot_uniqueid'])
            dlog("I have no owner.");
            dlog("");
            dlog("Use the Unique ID with '!owner ...' on IRC to claim this bot.");
            dlog("");
            dlog("Until claimed, only the 'owner' module will be loaded,");
            dlog("after claiming the other modules will be auto loaded.");
            dlog("");
            self.load_module("owner");

        # Compile configurable regexps for matching in event handlers
        self.re_trigger = re.compile(self.state['bot_trigger_re'])
        self.re_command = re.compile(self.state['bot_trigger_re'] + self.state['bot_command_re'])

        self.setup_udp_listener()

        # These settings were introduced later on and will break existing installs on "upgrade".
        if 'max_output_lines' not in self.state:
            self.state['max_output_lines'] = 3
        if 'ignore_max_output_lines' not in self.state:
            self.state['ignore_max_output_lines'] = False
        if 'max_output_line_length' not in self.state:
            self.state['max_output_line_length'] = 200
        if 'ignore_max_output_line_length' not in self.state:
            self.state['ignore_max_output_line_length'] = False

        self.save_obj_as_json(self.state, self.state['bot_config'])

        weechat.hook_signal("*,irc_in2_privmsg",  "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_join",     "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_part",     "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_quit",     "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in_topic",     "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_topic",    "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_invite",   "shim_wcb_handle_event",     "")

        # reoplist (chan mode +R) module signal plumbing, only on IRCNet
        weechat.hook_signal("ircnet,irc_in2_344", "shim_wcb_handle_event",     "")
        weechat.hook_signal("ircnet,irc_in2_345", "shim_wcb_handle_event",     "")

        self.alarms = self.load_obj_from_json(self.state['bot_alarms'])
        if not isinstance(self.alarms, list):
            self.alarms = []

        weechat.hook_timer(60 * 1000, 0, 0, "shim_wcb_handle_timer_signal", "")

        dlog("\nWeeChatBot initialization complete!")



    ''' WeeChat hooks and triggers '''
    def wcb_handle_event(self, data, signal, signal_data):
        self.event = {}
        self.output = []
        self.event['server'], self.event['signal'] = signal.split(",")
        if self.state['debug_event']:
            dlog("Event: %s" % signal)
        for k, v in self.weechat.info_get_hashtable("irc_message_parse", {"message": signal_data}).items():
            self.event[k] = v
        self.event['channel'] = self.event['channel'].lower()
        self.event['target_username'] = self.event['server'] + '.' + self.event['nick']
        self.event['target_channel'] = self.event['server'] + '.' +  self.event['channel']
        self.event['command'] = self.event['command_args'] = self.event['trigger'] = ''
        self.event['nickmask'] = self.event['host']
        res = self.re.match("^.*!(.*)", self.event['host'])
        if res:
            self.event['hostmask'] = res.group(1).lower()
        else:
            # This is an IRCNet 'reop list' event, set the bot as originator for permission reasons.
            if self.event['server'] == 'ircnet' and self.event['signal'] in ['irc_in2_344', 'irc_in2_345']: # XXX perhaps do this for all numeric irc_in2_NNN events?
                self.event['hostmask'] = 'self@host'
                self.event['nickmask'] = 'WeeChatBot!self@host'
        del self.event['host']

        # Remove clutter
        for key in ['pos_arguments', 'pos_channel', 'pos_command', 'pos_text']:
            self.event.pop(key, None)

        # Find the WeeChat buffer for this event
        self.find_buffer_for_event()

        # Deal with 'grep'-functionality.
        if ' | grep ' in self.event['text']:
            res = self.re.match(r'^(.*)\s\|\sgrep\s(.*)', self.event['text'])
            self.event['orig_text'] = self.event['text']
            self.event['text'] = res.group(1)
            self.event['search_for'] = res.group(2)

        # Check for a "!command args" style event, set appropriate values.
        re_trigger_result = self.re_trigger.search(self.event['text'])
        re_command_result = self.re_command.search(self.event['text'])
        if re_trigger_result and re_command_result:
            self.event['command'] = re_command_result.group(1)
            self.event['command'] = self.event['command'].lower()
            if re_command_result.group(2):
                self.event['command_args'] = re.sub(r'^\s+', '', re.sub(r'\s+$', '', re_command_result.group(2)))

        # Fetch the event originator's user info
        self.event['user_info'] = self.db_get_userinfo_by_userhost(self.event['hostmask'])
        return self.let_module_handle_event()


    def find_buffer_for_event(self):
        # Find the correct reply buffer. If 'channel' for event does not
        # look like an IRC-channel it probably is a nickname (private message)
        # so adjust target accordingly.
        reply_buffer_name = self.event['target_channel']
        self.event['is_privmsg'] = False
        if not re.match('^[#&]', self.event['channel']):
            reply_buffer_name = self.event['target_username']
            self.event['is_privmsg'] = True

        # Find the actual buffer, not all signals are associated with a single buffer, so we skip them.
        self.event['weechat_buffer'] = False
        if self.event['signal'] not in ['irc_in2_QUIT', 'irc_in2_INVITE']:
            reply_buffer = self.weechat.buffer_search("irc", '(?i)' + reply_buffer_name) # (?i) case insensitive
            if not reply_buffer:
                dlog("Could not find reply_buffer for event: '%s'" % self.event)
            self.event['weechat_buffer'] = reply_buffer

        # If this is a JOIN event, update WeeChat internal state with gratouitous '/WHO' on the channel.
        # We need to do this here, so the next bot_nick and related info is accurate.
        if self.event['signal'] == 'irc_in2_JOIN':
            self.weechat.command(self.event['weechat_buffer'], '/who ' + self.event['channel'])

        # Find our name on the event's buffer
        self.event['bot_nick'] = 'no_event_buffer'
        if self.event['weechat_buffer']:
            for t in [('bot_nick', 'localvar_nick'), ('bot_hostmask', 'localvar_host')]:
                value = self.weechat.buffer_get_string(self.event['weechat_buffer'], t[1])
                self.event[t[0]] = value

            if 'bot_hostmask' in self.event:
                self.event['bot_nickmask'] = self.event['bot_nick'] + '!' + self.event['bot_hostmask']
            else:
                dlog("Could not find our own nick/host on buffer?")
                self.debug_event(event)
                self.event['bot_nick'] = 'undef'
                self.event['bot_hostmask'] = 'undef@undef.undef'
                self.event['bot_nickmask'] = 'undef!undef@undef.undef'

            self.weechat.infolist_free(value)

        # Check if bot is op on event's channel.
        self.event['bot_is_op'] = False
        infolist = self.weechat.infolist_get('irc_nick', '', '%s,%s' % (self.event['server'], self.event['channel']))
        while self.weechat.infolist_next(infolist):
            nick = self.weechat.infolist_string(infolist, 'name')
            if nick != self.event['bot_nick']:
                continue
            if '@' in self.weechat.infolist_string(infolist, 'prefix'):
                self.event['bot_is_op'] = True
                break
        self.weechat.infolist_free(infolist)
        return


    def let_module_handle_event(self, handle_event_silently=False):
        # Log the event!
        if self.state['debug_event']:
            self.debug_event()

        # Look for modules to handle this event.
        event_command_handled = 0
        self.event['trigger'] = ''
        run_modules = []

        # First try finding modules that trigger by a command
        for module in list(self.modules):
            if self.event['command'] in self.modules[module]['commands']:
                if not self.perms(self.modules[module]['permissions']):
                    dlog("Moduile '%s' would handle this event but permissions mismatch." % module)
                    continue
                self.event['trigger'] = 'command'
                run_modules.append(module)

        # Then look for modules that trigger on events
        if not run_modules:
            for module in list(self.modules):
                if self.event['signal'] in self.modules[module]['events']:
                    if not self.perms(self.modules[module]['permissions']):
                        dlog("Moduile '%s' would handle this event but permissions mismatch." % module)
                        continue
                    self.event['trigger'] = 'event'
                    run_modules.append(module)

        # If no module was found, just return OK
        if not run_modules:
            return self.weechat.WEECHAT_RC_OK

        # Multiple modules can claim a command or event. Event is more likely.
        for run_module in run_modules:
            if not handle_event_silently or self.state['debug_event'] is True:
                dlog("Module '%s' handles '%s' by '%s' method." % (run_module, self.event['signal'], self.event['trigger']))

            module_return_state = self.signal_cont
            try:
                module_return_state = self.modules[run_module]['object'].run(self, self.event)
                if not module_return_state:
                    module_return_state = self.signal_cont
            except Exception as err:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                while 1:
                    if not exc_traceback.tb_next:
                        break
                    exc_traceback = exc_traceback.tb_next
                frame = exc_traceback.tb_frame
                mod_name = os.path.basename(frame.f_code.co_filename)[:-3]
                rtxt = "Error in %s line %s: %s" % (frame.f_code.co_filename, frame.f_lineno, err)
                if self.event['weechat_buffer']:
                    self.say(rtxt)
                    self.wcb_do_output()
                return dlog(rtxt)

            if module_return_state == self.signal_stop:
                self.wcb_do_output()
                return self.weechat.WEECHAT_RC_OK

        # Try event again as infoitem lookup (!foo?) when command and not handled
        # unless someone types !!!! for example.
        text_has_double_trigger_char = self.re_trigger.search(self.event['text'][1:])
        if 'infoitem' in self.modules and not text_has_double_trigger_char and not self.event['trigger'] == 'command':
            if ' | grep ' in self.event['text']:
                res = self.re.match(r'^(.*)\s\|\sgrep\s(.*)', self.event['text'])
                self.event['orig_text'] = self.event['text']
                self.event['text'] = res.group(1)
                self.event['search_for'] = res.group(2)
            self.event['text'] += "?"
            self.event['trigger'] = 'event'
            self.event['infoitem_auto_lookup_quiet'] = True
            self.modules['infoitem']['object'].run(self, self.event)

        self.wcb_do_output()
        return self.weechat.WEECHAT_RC_OK


    def wcb_do_output(self):
        search_for = ''
        if 'search_for' in self.event:
            search_for = self.event['search_for']

        if not self.output:
            return

        real_output_lines = []
        max_line_length = 0
        for output_dict in self.output:
            if 'arr' in output_dict:
                output_line = ''
                for elem in output_dict['arr']:
                    if search_for not in elem:
                        continue
                    output_line += f" .. {elem}"
                output_line = output_line[4:] # strip leading ' .. '
                output_dict['msg'] = output_line
                output_dict.pop('arr', None)
            else:
                if search_for not in output_dict['msg']:
                    continue
            max_line_length = len(output_dict['msg']) if len(output_dict['msg']) > max_line_length else max_line_length
            real_output_lines.append(output_dict)

        did_output = False
        force_private = False
        if not self.state['ignore_max_output_lines'] and len(real_output_lines) > self.state['max_output_lines']:
            self.weechat.command(self.event['weechat_buffer'], f"There's more than {self.state['max_output_lines']} lines of output, i'll message you privately.")
            force_private = True

        if not self.state['ignore_max_output_line_length'] and max_line_length > self.state['max_output_line_length']:
            self.weechat.command(self.event['weechat_buffer'], f"There's line(s) longer than {self.state['max_output_line_length']} characters in the result(s), i'll message you privately.")
            force_private = True

        for line in real_output_lines:
            if self.re.search(r'^\s*$', line['msg']):
                continue
            if force_private:
                line['type'] = 'private'
            if line['type'] == 'say':
                self.weechat.command(self.event['weechat_buffer'], line['msg'])
                did_output = True
            elif line['type'] == 'private':
                self.weechat.command(self.event['weechat_buffer'], '/msg %s %s' % (self.event['nick'], line['msg']))
                did_output = True

        if not did_output and 'search_for' in self.event:
            if self.event['is_privmsg']:
                self.weechat.command(self.event['weechat_buffer'], '/msg %s nothing matched your search criteria!' % (self.event['nick']))
            else:
                self.weechat.command(self.event['weechat_buffer'], 'nothing matched your search criteria!')

        self.output = []
        return self.weechat.WEECHAT_RC_OK


    def wcb_handle_timer_signal(self, data, remaining_calls):
        self.event = {
            'data': data,
            'remaining_calls': remaining_calls,

            'arguments': '',
            'bot_is_op': False,
            'bot_nick': '',
            'channel': '',
            'command': '',
            'command_args': '',
            'hostmask': 'weechatbot@self',
            'message_without_tags': ':WeeChatBot!self@host ALARMTIMER '
                                    ':Alarm timer event',
            'nick': 'WeeChatBot',
            'nickmask': 'WeeChatBot!self@host',
            'server': '',
            'signal': 'timer_signal',
            'tags': '',
            'target_channel': '',
            'target_username': '',
            'text': '',
            'trigger': '',
            'user': '',
            'user_info': None,
            'weechat_buffer': None
        }
        return self.let_module_handle_event(handle_event_silently=True)


    def hook_process(self, fn_or_cmd, timeout):
        """ Save some state from the event that led to this hook_process
        call so the call back event is able to route back messages.
        WeeChat can only pass a string around, so we'll use JSON. We
        need to copy data from the original event: simply dumps()'ing
        the entire self.event dict doesn't work as for example
        self.event['weechat_buffer'] is not representable in JSON.
        """
        callback_event = {
            'server': self.event['server'],
            'channel': self.event['channel'],
            'nick': self.event['nick'],
            'nickmask': self.event['nickmask'],
            'hostmask': self.event['hostmask'],
            'target_channel': self.event['target_channel'],
            'target_username': self.event['target_username'],
            'user': self.event['user'],
            'command': self.event['command'],
            'command_args': self.event['command_args'],
        }
        self.weechat.hook_process(fn_or_cmd, timeout, "shim_wcb_hook_process_callback", json.dumps(callback_event))
        return self.weechat.WEECHAT_RC_OK


    def wcb_handle_hook_process_callback(self, callback_data, process, process_rc, process_stdout, process_stderr):
        # Construct an event dict, assuming keys are copied from callback_data
        self.event = {
            'process': process,
            'process_rc': process_rc,
            'process_stdout': process_stdout,
            'process_stderr': process_stderr,

            'arguments': '',
            'message_without_tags': ':WeeChatBot!self@host HOOKPROCESSCALLBACK '
                                    ':Hook process callback event',
            'signal': 'hook_process_callback',
            'tags': '',
            'text': '',
            'trigger': '',
            'user': '',
            'user_info': None,
            'weechat_buffer': None
        }

        # Copy over the callback_data provided event info
        callback_data_dict = json.loads(callback_data)
        for key in callback_data_dict:
            self.event[key] = callback_data_dict[key]

        # Try to find a matching buffer for this callback
        self.find_buffer_for_event()
        # Try to find matching user_info for this callback
        self.event['user_info'] = self.db_get_userinfo_by_userhost(self.event['hostmask'])

        # Catch hook errors
        if self.event['process_rc'] == self.weechat.WEECHAT_HOOK_PROCESS_ERROR:
            dlog("hook_process error with command '%s'" % self.event['process'])
            return wcb.say("hook_process error with command '%s'" % self.event['process'])
        return self.let_module_handle_event(handle_event_silently=True)


    def wcb_handle_buffer_input(self, data, buffer, input_data):
        self.weechat.prnt(buffer, "Bot control via this buffer hasn't been implemented yet! Your input was: %s" % input_data)
        return self.weechat.WEECHAT_RC_OK


    def wcb_unload(self):
        if self.udp_socket_open == True:
            self.udp_socket.close()
        self.save_obj_as_json(self.state, self.state['bot_config'])
        return self.weechat.WEECHAT_RC_OK



    '''
    UDP Listener
    UDP 'protocol' definition:
    Gozerbot style '<password> <channel> <...message...>'
      or
    WeeChatBot style '<password> <servername> <channel> <...message...>'
    WeeChatBot could be on the same channel on different networks.
    '''
    def setup_udp_listener(self):
        for key in ['udp_listen_ip', 'udp_listen_port', 'udp_listen_pass']:
            if key in self.state and self.state[key] == '':
                return dlog("UDP listener disabled: missing '%s' setting" % key)
        if self.udp_socket_open == True:
            self.udp_socket.close()
            self.udp_socket_open = False
        self.udp_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.udp_socket.bind((self.state['udp_listen_ip'], self.state['udp_listen_port']))
        self.udp_socket_open = True
        hook = weechat.hook_fd(self.udp_socket.fileno(), 1, 0, 0, "shim_wcb_handle_udp_input", "")
        dlog("UDP listener started at [%s]:%s!" % (self.state['udp_listen_ip'], self.state['udp_listen_port']))


    def wcb_handle_udp_input(self, data, fd):
        sock = socket.fromfd(fd, socket.AF_INET6, socket.SOCK_DGRAM)
        data, addr = sock.recvfrom(1024)
        host, port = socket.getnameinfo(addr, socket.NI_NUMERICHOST | socket.NI_NUMERICSERV)
        try:
            str_data = data.decode('utf-8')
        except Exception as err:
            return dlog("UDP message from [%s]:%s did not decode as valid UTF-8: '%s'" % (host, port, data))

        # Expect -at least- three words input
        # Password TargetChannel Message[..]
        re_sult = re.match('^(\S+)\s+(\S+)\s+(.*)', str_data)
        if not re_sult:
            return dlog("UDP message from [%s]:%s not properly formed: '%s'" % (host, port, data))

        password = re_sult.group(1)
        channel  = re_sult.group(2)
        message  = re_sult.group(3)

        if password != self.state['udp_listen_pass']:
            return dlog("UDP message from [%s]:%s had bad password: '%s'" % (host, port, data))

        if not message:
            return dlog('UDP message from [%s]:%s had empty message!' % (host, port))

        # Make passing message to weechat.command() "safer" by replacing leading '/'-chars :)
        if message[0] == '/':
            message = '_' + message[1:]
        message = message.replace('\\', '\\\\')

        # Check if channel is indeed the channel, or the server name.
        # If it smells like a server name, strip of the next word from
        # str_data to use as the new channel name.
        server = 'undef'
        if not re.match('^[#&]', channel):
            server = channel
            re_sult = re.match('^(\S+)\s', message)
            if not re_sult:
                dlog("UDP message from [%s]:%s failed to properly parse: '%s'" % (host, port, str_data))
                return self.weechat.WEECHAT_RC_ERROR
            channel = re_sult.group(1)
            if not re.match('^[#&]', channel):
                dlog("This '%s' does not look like a channel name" % channel)
                dlog("UDP message from [%s]:%s failed to properly parse: '%s'" % (host, port, str_data))
                return self.weechat.WEECHAT_RC_ERROR
            message = re.sub('^(\S+)\s', '', message)

        if self.state['debug_udp']:
            dlog("UDP message from [%s]:%s to '%s.%s': '%s'" % (host, port, server, channel, message))

        if server == 'undef': # Search for first matching buffer in any server
            servers = self.weechat.infolist_get("irc_server", "", "")
            while self.weechat.infolist_next(servers):
                irc_server_name = self.weechat.infolist_string(servers, "name")
                target = irc_server_name + '.' + channel
                udp_output_buffer = self.weechat.buffer_search('irc', '(?i)'+target) # (?i) case insensitive
                if udp_output_buffer:
                    self.weechat.command(udp_output_buffer, message)
                    if self.state['debug_udp']:
                        dlog("Found channel '%s' in server '%s'" % (channel, irc_server_name))
                    self.weechat.infolist_free(servers)
                    return weechat.WEECHAT_RC_OK
            self.weechat.infolist_free(servers)
            return dlog("Could not find '%s' buffer in any irc_server." % (channel))

        target = server + '.' + channel
        udp_output_buffer = self.weechat.buffer_search('irc', '(?i)'+target) # (?i) case insensitive
        if udp_output_buffer:
            self.weechat.command(udp_output_buffer, message)
            return weechat.WEECHAT_RC_OK

        dlog("Could not find '%s' buffer in '%s' irc_server." % (channel, server))
        dlog("UDP message from [%s]:%s to '%s.%s': '%s'" % (host, port, server, channel, message))
        return self.weechat.WEECHAT_RC_ERROR



    ''' Functions pertaining to configuration files '''
    def save_obj_as_json(self, object, dstfile):
        try:
            tmp = tempfile.NamedTemporaryFile(mode='w', delete=False, prefix='wcb_tmp_', suffix='.json')
            tmp.write(json.dumps(object, sort_keys=True, indent=4))
            tmp.close()
            shutil.move(tmp.name, dstfile)
        except Exception as e:
            return dlog("Can't write file '%s': %s" % (dstfile, e))
        return True


    def load_obj_from_json(self, srcfile):
        try:
            input = open(srcfile, 'r')
        except Exception as e:
            return dlog("Can't read file '%s': %s" % (srcfile, e))
        object = json.load(input)
        input.close()
        return object


    ''' Module loading, unloading, reloading '''
    def load_all_modules(self):
        mods = []
        for ent in os.listdir(self.state['bot_modules']):
            if ent[-3:] != '.py':
                continue
            mods.append(self.state['bot_modules'] + '/' + ent)
        for ent in os.listdir(self.state['bot_extra_modules']):
            if ent[-3:] != '.py':
                continue
            mods.append(self.state['bot_extra_modules'] + '/' + ent)
        for mod in mods:
            self.load_module(mod, quiet=True)
        mlist = ", ".join(self.modules.keys())
        return dlog("Loaded modules: [%s]" % mlist)


    def load_module(self, module, quiet=False):
        module_name = os.path.basename(module)
        if '.py' in module[-3:]:
            module_name = os.path.basename(module[:-3])

        if '/' not in module:
            module_full_path = self.state['bot_modules'] + '/' + module + '.py'
            if not os.path.exists(module_full_path):
                module_full_path = self.state['bot_extra_modules'] + '/' + module + '.py'
        else:
            module_full_path = module

        module_object = ''
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_full_path)
            module_object = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module_object
            spec.loader.exec_module(module_object)
        except Exception as e:
            rstr = "Loading module '%s' failed: %s" % (module_name, e)
            dlog(rstr)
            return rstr

        if not hasattr(module_object, 'config'):
            rstr = "Module '%s' loaded, but does not have a config() function. Failed." % (module_name)
            dlog(rstr)
            return rstr

        module_config = module_object.config(self)
        for test_key in ['events', 'commands', 'help']:
            if test_key not in module_config:
                rstr = "Module '%s' config does not provide '%s' key. Failed." % (module_name, test_key)
                dlog(rstr)
                return rstr

        module_config['object'] = module_object
        self.modules[module_name] = module_config
        if not quiet:
            rstr = "Module '%s' loaded succesfully." % module_name
            dlog(rstr)
            return rstr

        return "OK"


    def unload_module(self, module_name):
        if '.py' in module_name[-3:]:
            module_name = module_name[:-3]

        if module_name not in self.modules:
            return dlog("A module named '%s' was not found loaded." % module_name)

        # Python cant "unload" modules, so this just
        # removes the internal reference to the module
        del self.modules[module_name]
        return dlog("Module '%s' unloaded succesfully." % module_name)



    ''' Database related functions '''
    def db_connect(self):
        try:
            pg_conn = psycopg2.connect(user = self.state['db_user'],
                        password = self.state['db_pass'],
                        host = self.state['db_host'],
                        port = self.state['db_port'],
                        dbname = self.state['db_name'])
        except (Exception, psycopg2.Error) as err:
            return dlog("Error while connecting to PostgreSQL: %s" % err)
        return pg_conn


    def db_get_userinfo_by_ircnick(self, tnick):
        # Find referenced nick name in the originating event channel
        infolist = self.weechat.infolist_get('irc_nick', '', '%s,%s' % (self.event['server'], self.event['channel']))
        tuserhost = ''
        while self.weechat.infolist_next(infolist):
            nick = self.weechat.infolist_string(infolist, 'name')
            if nick.lower() != tnick.lower():
                continue
            host = self.weechat.infolist_string(infolist, 'host')
            if host == '':
                self.say("Sorry, try that again?")
                self.weechat.infolist_free(infolist)
                return self.weechat.WEECHAT_RC_OK
            tuserhost = host
        self.weechat.infolist_free(infolist)
        return self.db_get_userinfo_by_userhost(tuserhost.lower())


    def db_get_userinfo_by_userhost(self, host):
        ret = {}
        host = host.lower()

        db = self.db_connect()
        cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)

        sql = "SELECT h.hostmask AS current_hostmask, u.* FROM wcb_hostmasks h, wcb_users u WHERE h.users_id = u.id AND h.hostmask = %s"
        cur.execute(sql, (host,))
        db_res = cur.fetchall()
        if not db_res:
            return None
        db_res = db_res[0]
        for key in db_res.keys():
            ret[key] = db_res[key]

        ret['permissions'] = {
            'global': []
        }

        sql = "SELECT permission, channel FROM wcb_perms WHERE users_id = %s"
        cur.execute(sql, (ret['id'],))
        db_res = cur.fetchall()
        for row in db_res:
            if row['channel'] and row['channel'] != '':
                if row['channel'] not in ret['permissions']:
                    ret['permissions'][row['channel']] = []
                ret['permissions'][row['channel']].append(row['permission'])
            else:
                ret['permissions']['global'].append(row['permission'])

        ret['hostmasks'] = []
        sql = "SELECT hostmask FROM wcb_hostmasks WHERE users_id = %s"
        cur.execute(sql, (ret['id'],))
        db_res = cur.fetchall()
        for row in db_res:
            for k in row.keys():
                ret['hostmasks'].append(row[k])

        cur.close()
        db.close()
        if ret == None:
            return None
        return ret


    def db_get_userinfo_by_username(self, username):
        ret = {}
        username = username.lower()

        db = self.db_connect()
        cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)

        sql = "SELECT h.hostmask AS current_hostmask, u.* FROM wcb_hostmasks h, wcb_users u WHERE h.users_id = u.id AND u.username = %s"
        cur.execute(sql, (username,))
        db_res = cur.fetchall()
        if not db_res:
            return None
        db_res = db_res[0]
        for key in db_res.keys():
            ret[key] = db_res[key]

        ret['permissions'] = {
            'global': []
        }

        sql = "SELECT permission, channel FROM wcb_perms WHERE users_id = %s"
        cur.execute(sql, (ret['id'],))
        db_res = cur.fetchall()
        for row in db_res:
            if row['channel'] and row['channel'] != '':
                if row['channel'] not in ret['permissions']:
                    ret['permissions'][row['channel']] = []
                ret['permissions'][row['channel']].append(row['permission'])
            else:
                ret['permissions']['global'].append(row['permission'])

        ret['hostmasks'] = []
        sql = "SELECT hostmask FROM wcb_hostmasks WHERE users_id = %s"
        cur.execute(sql, (ret['id'],))
        db_res = cur.fetchall()
        for row in db_res:
            for k in row.keys():
                ret['hostmasks'].append(row[k])

        cur.close()
        db.close()
        if ret == None:
            return None
        return ret



    ''' Functions useful to modules '''
    def debug_event(self):
        pp = pprint.PrettyPrinter(indent=4)
        dlog("Event:\n%s" % pp.pformat(self.event))

    def mlog(self, message):
        caller = inspect.getouterframes(inspect.currentframe(), 2)[1][1]
        caller = caller[:-3]
        caller = caller.split('/')[-1]
        mlog_buffer = self.weechat.buffer_search('python', 'WeeChatBot')
        for ln in message.split("\n"):
            weechat.prnt(mlog_buffer, "%s | %s" % (caller, ln))
        return self.weechat.WEECHAT_RC_OK


    def reply(self, message, immediate=False):
        if type(message) == list:
            self.output.append({'type': 'say', 'arr': message})
        else:
            reply = "%s, %s" % (self.event['nick'], message)
            self.output.append({'type': 'say', 'msg': reply})
        if immediate:
            self.wcb_do_output()
        return self.weechat.WEECHAT_RC_OK

    def say(self, message, immediate=False):
        if type(message) == list:
            self.output.append({'type': 'say', 'arr': message})
        else:
            self.output.append({'type': 'say', 'msg': message})
        if immediate:
            self.wcb_do_output()
        return self.weechat.WEECHAT_RC_OK

    def private(self, message, immediate=False):
        if type(message) == list:
            self.output.append({'type': 'private', 'arr': message})
        else:
            self.output.append({'type': 'private', 'msg': message})
        if immediate:
            self.wcb_do_output()
        return self.weechat.WEECHAT_RC_OK


    def perm(self, want_perms): return self.perms(want_perms)
    def perms(self, want_perms, explicit=False):
        if not isinstance(want_perms, list):
            want_perms = [want_perms] # make list if not a list
        if not want_perms: # module has no perms
            return True
        if explicit is False and self.state['bot_ownermask'] == self.event['nickmask']: # owner, always
            return True
        if self.event['nickmask'] == 'WeeChatBot!self@host': # internal event, always
            return True
        if not self.event['user_info']: # unrecognized user
            return False
        if explicit is False and 'owner' in self.event['user_info']['permissions']['global']: # owner, by permission
            return True
        channel = self.event['channel'].lower()
        for want_perm in want_perms:
            if 'chan-perm' in self.state and channel in self.state['chan-perm'] and want_perm in self.state['chan-perm'][channel]:
                return True
            if want_perm in self.event['user_info']['permissions']['global']:
                return True
            if channel in self.event['user_info']['permissions'] and want_perm in self.event['user_info']['permissions'][channel]:
                return True
        return False


    def get_userhost_by_ircnick(self, tnick):
        # Find referenced nick name in the originating event channel
        infolist = self.weechat.infolist_get('irc_nick', '', '%s,%s' % (self.event['server'], self.event['channel']))
        tuserhost = None
        while self.weechat.infolist_next(infolist):
            nick = self.weechat.infolist_string(infolist, 'name')
            if nick.lower() != tnick.lower():
                continue
            host = self.weechat.infolist_string(infolist, 'host')
            if host == '':
                self.weechat.command(self.event['weechat_buffer'], '/who ' + self.event['channel'])
                self.say('OOPS: WeeChat stale data. Try again!')
                self.weechat.infolist_free(infolist)
                return self.weechat.WEECHAT_RC_OK
            tuserhost = host.lower()
        self.weechat.infolist_free(infolist)
        return tuserhost
