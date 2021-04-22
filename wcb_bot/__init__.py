# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import random
import pprint
import socket
import weechat
import inspect
import psycopg2
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

        bot_output_buffer = self.weechat.buffer_new("WeeChatBot", "shim_wcb_handle_buffer_input", "", "", "")
        self.buffer = bot_output_buffer

        bot_base = os.environ['HOME'] + '/.weechat/python/wcb_bot'
        self.udp_socket_open = False
        self.modules = {}
        self.state = {
            'bot_base':          bot_base,
            'bot_modules':       '%s/modules' % bot_base,
            'bot_extra_modules': '%s/extra_modules' % bot_base,
            'bot_config':        '%s/wcb_config.json' % bot_base,
            'bot_alarms':        '%s/wcb_alarms.json' % bot_base,

            'bot_uniqueid':  ''.join(random.sample('abcdefghijklmnopqrstuvwxyzABCFEFGHIJKLMNOPQRSTUVWXYZ1234567890', 8)),
            'bot_ownermask': '',

            'bot_trigger_re': '^[!\.]',

            # This regexp must return the command and the 'arguments' via (grou)(ping)
            'bot_command_re': '([-a-zA-Z0-9]+)(?:\s(.*)|$)',

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

        self.save_obj_as_json(self.state, self.state['bot_config'])

        weechat.hook_signal("*,irc_in2_privmsg", "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_join",    "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_part",    "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_quit",    "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in_topic",    "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_topic",   "shim_wcb_handle_event",     "")
        weechat.hook_signal("*,irc_in2_invite",  "shim_wcb_handle_event",     "")

        self.alarms = self.load_obj_from_json(self.state['bot_alarms'])
        if not isinstance(self.alarms, list):
            self.alarms = []

        weechat.hook_timer(60 * 1000, 0, 0, "shim_wcb_handle_timer_signal", "")

        dlog("\nWeeChatBot initialization complete!")



    ''' WeeChat hooks and triggers '''
    def wcb_handle_event(self, data, signal, signal_data):
        event = {}
        event['server'], event['signal'] = signal.split(",")
        for k, v in self.weechat.info_get_hashtable("irc_message_parse", {"message": signal_data}).items():
            event[k] = v
        event['target_username'] = event['server'] + '.' + event['nick']
        event['target_channel'] = event['server'] + '.' +  event['channel']
        event['command'] = event['command_args'] = event['trigger'] = ''
        event['nickmask'] = event['host']
        res = self.re.match("^.*!(.*)", event['host'])
        event['hostmask' ] = res.group(1)
        del event['host']

        # Remove clutter
        for key in ['pos_arguments', 'pos_channel', 'pos_command', 'pos_text']:
            event.pop(key, None)

        # Check for a "!command args" style event, set appropriate values.
        re_trigger_result = self.re_trigger.search(event['text'])
        re_command_result = self.re_command.search(event['text'])
        if re_trigger_result and re_command_result:
            event['command'] = re_command_result.group(1)
            event['command'] = event['command'].lower()
            if re_command_result.group(2):
                event['command_args'] = re.sub('^\s+', '', re.sub('\s+$', '', re_command_result.group(2)))

        # Find the correct reply buffer. If 'channel' for event does not
        # look like an IRC-channel it probably is a nickname (private message)
        # so adjust target accordingly.
        reply_buffer_name = event['target_channel']
        if not re.match('^[#&]', event['channel']):
            reply_buffer_name = event['target_username']

        # Find the actual buffer, not all signals are associated with a single buffer, so we skip them.
        event['weechat_buffer'] = False
        if event['signal'] not in ['irc_in2_QUIT', 'irc_in2_INVITE']:
            reply_buffer = self.weechat.buffer_search("irc", '(?i)' + reply_buffer_name) # (?i) case insensitive
            if not reply_buffer:
                dlog("Could not find reply_buffer for event: '%s'" % event)
            event['weechat_buffer'] = reply_buffer

        # If this is a JOIN event, update WeeChat internal state with gratouitous '/WHO' on channel
        if event['signal'] == 'irc_in2_JOIN':
            self.weechat.command(event['weechat_buffer'], '/who ' + event['channel'])

        # Find our name on event's channel
        event['bot_nick'] = 'no_event_buffer'
        if event['weechat_buffer']:
            bot_nick = self.weechat.buffer_get_string(event['weechat_buffer'], 'localvar_nick')
            event['bot_nick'] = bot_nick
            self.weechat.infolist_free(bot_nick)

        # Check if bot is op on event's channel.
        event['bot_is_op'] = False
        infolist = self.weechat.infolist_get('irc_nick', '', '%s,%s' % (event['server'], event['channel']))
        while self.weechat.infolist_next(infolist):
            nick = self.weechat.infolist_string(infolist, 'name')
            if nick != event['bot_nick']:
                continue
            if '@' in self.weechat.infolist_string(infolist, 'prefix'):
                event['bot_is_op'] = True
                break

        # Fetch the event originator's user info
        event['user_info'] = self.db_get_userinfo_by_userhost(event['hostmask'])
        self.event = event
        return self.let_module_handle_event(event)


    def let_module_handle_event(self, event, handle_event_silently=False):
        # Log the event!
        if self.state['debug_event']:
            pp = pprint.PrettyPrinter(indent=4)
            dlog("Event:\n%s" % pp.pformat(event))

        # Look for modules to handle this event.
        event_command_handled = 0
        for module in list(self.modules):
            event['trigger'] = ''

            if event['command'] in self.modules[module]['commands']:
                event['trigger'] = 'command'
            elif event['signal'] in self.modules[module]['events']:
                event['trigger'] = 'event'

            # Found one?
            if event['trigger']:
                # Check permissions and run if allowed.
                if not self.perms(self.modules[module]['permissions']):
                    dlog("Moduile '%s' would handle this event but permissions mismatch." % module)
                    continue

                if event['trigger'] == 'command':
                    event_command_handled = 1

                if not handle_event_silently or self.state['debug_event'] is True:
                    dlog("Module '%s' handles '%s' by '%s' method." % (module, event['signal'], event['trigger']))

                try:
                    self.modules[module]['object'].run(self, event)
                except Exception as err:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    while 1:
                        if not exc_traceback.tb_next:
                            break
                        exc_traceback = exc_traceback.tb_next
                    frame = exc_traceback.tb_frame
                    mod_name = os.path.basename(frame.f_code.co_filename)[:-3]
                    rtxt = "Error in %s line %s: %s" % (frame.f_code.co_filename, frame.f_lineno, err)
                    if event['weechat_buffer']:
                        self.say(rtxt)
                    return dlog(rtxt)

        # Try event again as infoitem lookup (!foo?) when command and not handled
        # This is fugly. Modules should return some kind of return code indicating
        # wether events should propagate or be considered dealth with.
        if not event_command_handled \
            and event['command'] != '' \
            and event['command'] != 'forget' \
            and " = " not in event['text'] \
            and not event['text'].endswith('++') \
            and not event['text'].endswith('--'):
                event['text'] += "?"
                event['trigger'] = 'event'
                self.modules['infoitem']['object'].run(self, event)

        return self.weechat.WEECHAT_RC_OK


    def wcb_handle_timer_signal(self, data, remaining_calls):
        timer_signal = {
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
        self.event = timer_signal
        return self.let_module_handle_event(timer_signal, handle_event_silently=True)


    def wcb_handle_buffer_input(self, data, buffer, input_data):
        self.weechat.prnt(buffer, "Your input was: %s" % input_data)
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
            if self.state[key] and self.state[key] == '':
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
        message.replace("\0", "[null]")

        # Check if channel is indeed the channel, or the server name.
        # If it smells like a server name, strip of the next word from
        # str_data to use as the new channel name.
        server = 'undef'
        if not re.match('^[#&]', channel):
            server = channel
            re_sult = re.match('^(\S+)\s', message)
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
            dlog("Could not find '%s' buffer in any irc_server." % (channel))
        else:
            target = server + '.' + channel
            udp_output_buffer = self.weechat.buffer_search('irc', '(?i)'+target) # (?i) case insensitive
            if udp_output_buffer:
                self.weechat.command(udp_output_buffer, message)
                return weechat.WEECHAT_RC_OK
            else:
                dlog("Could not find '%s' buffer in '%s' irc_server." % (channel, server))
                dlog("UDP message from [%s]:%s to '%s.%s': '%s'" % (host, port, server, channel, message))
                return self.weechat.WEECHAT_RC_ERROR



    ''' Functions pertaining to configuration files '''
    def save_obj_as_json(self, object, dstfile):
        try:
            output = open(dstfile, 'w')
        except Exception as e:
            return dlog("Can't write file '%s': %s" % (dstfile, e))
        output.write(json.dumps(object, sort_keys=True, indent=4))
        output.close()
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
            if nick != tnick:
                continue
            host = self.weechat.infolist_string(infolist, 'host')
            if host == '':
                self.say("Sorry, try that again?")
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
    def mlog(self, message):
        caller = inspect.getouterframes(inspect.currentframe(), 2)[1][1]
        caller = caller[:-3]
        caller = caller.split('/')[-1]
        mlog_buffer = self.weechat.buffer_search('python', 'WeeChatBot')
        for ln in message.split("\n"):
            weechat.prnt(mlog_buffer, "%s | %s" % (caller, ln))
        return self.weechat.WEECHAT_RC_OK


    def reply(self, message):
        reply = "%s, %s" % (self.event['nick'], message)
        self.weechat.command(self.event['weechat_buffer'], reply)
        return self.weechat.WEECHAT_RC_OK


    def say(self, message):
        self.weechat.command(self.event['weechat_buffer'], message)
        return self.weechat.WEECHAT_RC_OK


    def private(self, message):
        self.weechat.command(self.event['weechat_buffer'], '/msg %s %s' % (self.event['nick'], message))
        return self.weechat.WEECHAT_RC_OK


    def perm(self, want_perms): return self.perms(want_perms)
    def perms(self, want_perms):
        if not want_perms: # module has no perms
            return True
        if self.state['bot_ownermask'] == self.event['nickmask']: # owner, always
            return True
        if self.event['nickmask'] == 'WeeChatBot!self@host': # internal event, always
            return True
        if not self.event['user_info']: # unrecognized user
            return False
        if 'owner' in self.event['user_info']['permissions']['global']: # owner, by permission
            return True
        channel = self.event['channel'].lower()
        for want_perm in want_perms:
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
            if nick != tnick:
                continue
            host = self.weechat.infolist_string(infolist, 'host')
            if host == '':
                self.weechat.command(self.event['weechat_buffer'], '/who ' + self.event['channel'])
                self.say('OOPS: WeeChat stale data. Try again!')
                return self.weechat.WEECHAT_RC_OK
            tuserhost = host
        self.weechat.infolist_free(infolist)
        return tuserhost
