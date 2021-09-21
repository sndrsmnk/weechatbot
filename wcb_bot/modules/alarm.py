from datetime import datetime, timedelta
from dateutil.parser import parse
import re


def config(wcb):
    return {
        'events': ['timer_signal'],
        'commands': ['alarm', 'alarms', 'alarm-list', 'alarm-del'],
        'permissions': ['user'],
        'help': "Sets alarms",
    }


def alarm_list(wcb, event):
    if wcb.event['channel'] == wcb.event['bot_nick']: # privmsg
        alarm_where = wcb.event['target_username']
    else:
        alarm_where = wcb.event['target_channel']

    ctx = 0
    found_alarms = 0
    for elem in wcb.alarms:
        ctx += 1
        if elem['alarm_where'] != alarm_where:
            continue
        alarm_dt = datetime.fromtimestamp(elem['alarm_when'])
        wcb.say("[%d] '%s' at %s for %s" % (ctx, elem['alarm_text'], alarm_dt, elem['alarm_who']))
        found_alarms += 1

    if not found_alarms:
        return wcb.say('No alarms are set here!')


def alarm_add(wcb, event):
    now_date_obj = datetime.now()
    alarm_date_obj = None
    alarm_text = ''
    re_hhmm = re.compile(r'^(\d{1,2}:\d{2})(?::\d{2})?\s(.*)')
    re_ddmmhhmm = re.compile(r'^(\d{1,2})-(\d{1,2})\s(\d{1,2}:\d{2})(?::\d{2})?\s(.*)')
    re_ddmmyyyyhhmm = re.compile(r'^(\d{1,2})-(\d{1,2})-(\d{4})\s(\d{1,2}:\d{2})(?::\d{2})?\s(.*)')
    re_yyyymmddhhmm = re.compile(r'^(\d{4})-(\d{1,2})-(\d{1,2})\s(\d{1,2}:\d{2})(?::\d{2})?\s(.*)')

    res = re.match(re_hhmm, event['command_args'])
    if res:
        alarm_date_obj = parse(res.group(1))
        alarm_text = res.group(2)

    res = re.match(re_ddmmhhmm, event['command_args'])
    if res:
        dd = res.group(1)
        mm = res.group(2)
        hhmm = res.group(3)
        alarm_text = res.group(4)
        yy = datetime.now().year
        dstr = "%s-%s-%s %s" % (mm, dd, yy, hhmm)
        alarm_date_obj = parse(dstr)

    res = re.match(re_ddmmyyyyhhmm, event['command_args'])
    if res:
        dd = res.group(1)
        mm = res.group(2)
        yyyy = res.group(3)
        hhmm = res.group(4)
        alarm_text = res.group(5)
        dstr = "%s-%s-%s %s" % (mm, dd, yyyy, hhmm)
        alarm_date_obj = parse(dstr)

    res = re.match(re_yyyymmddhhmm, event['command_args'])
    if res:
        dd = res.group(3)
        mm = res.group(2)
        yyyy = res.group(1)
        hh:mm = res.group(4)
        alarm_text = res.group(5)
        dstr = "%s-%s-%s %s" % (mm, dd, yyyy, hhmm)
        alarm_date_obj = parse(dstr)

    if not alarm_date_obj:
        wcb.say('Parsing of time failed. Usage: alarm <when> <text>')
        return wcb.say('<when> can be: HH:MM, dd-mm HH:MM, dd-mm-yyyy HH:MM, yyyy-mm-dd HH:MM')

    if alarm_date_obj < now_date_obj:
        wcb.say("We're already past '%s', assuming tomorrow." % alarm_date_obj)
        alarm_date_obj = alarm_date_obj + timedelta(days=1)
    
    if wcb.event['channel'] == wcb.event['bot_nick']: # privmsg
        alarm_where = wcb.event['target_username']
    else:
        alarm_where = wcb.event['target_channel']

    wcb.alarms.append({
        'alarm_text': alarm_text,
        'alarm_when': alarm_date_obj.timestamp(),
        'alarm_who': wcb.event['nick'],
        'alarm_where': alarm_where
    })

    wcb.save_obj_as_json(wcb.alarms, wcb.state['bot_alarms'])
    return wcb.say("[%d] '%s' at %s for %s" % (len(wcb.alarms), alarm_text, alarm_date_obj, wcb.event['nick']))


def alarm_del(wcb, event):
    if not event['command_args'].isnumeric():
        return wcb.reply('"%s" does not look like an number. Specify alarm index number to delete.' % e) #vent['command_args'])
    alarm_del_idx = int(event['command_args']) - 1

    if alarm_del_idx >= len(wcb.alarms) or alarm_del_idx < 0:
        return wcb.reply("hmmno, sorry. That would void the waranty.")

    if wcb.event['channel'] == wcb.event['bot_nick']: # privmsg
        alarm_where = wcb.event['target_username']
    else:
        alarm_where = wcb.event['target_channel']

    alarm_owner_nick = wcb.alarms[alarm_del_idx]['alarm_who']
    alarm_owner_where = wcb.alarms[alarm_del_idx]['alarm_where']

    if alarm_owner_where != alarm_where or alarm_owner_nick != event['nick']:
        return wcb.say("I can't let you do that, Dave. You don't own that alarm entry!")

    alarm_dt = datetime.fromtimestamp(wcb.alarms[alarm_del_idx]['alarm_when'])
    wcb.say('Alarm removed: "%s" at %s' % (wcb.alarms[alarm_del_idx]['alarm_text'], alarm_dt))
    del(wcb.alarms[alarm_del_idx])
    wcb.save_obj_as_json(wcb.alarms, wcb.state['bot_alarms'])
    return alarm_list(wcb,event)


def alarm_timer_event(wcb, event):
    """ This function can make no assumption on the event data. It is empty for the most part. """
    """ All message routing, if any, must be done with manual lookups of buffers and raw commands. """
    cur_dt = datetime.now()
    new_alarms = []
    do_save = 0

    for alarm_dict in wcb.alarms:
        if alarm_dict['alarm_when'] > cur_dt.timestamp():
            new_alarms.append(alarm_dict)
            continue

        res = re.match('^([^\.]+)\.(.*)', alarm_dict['alarm_where'])
        if not res:
            wcb.mlog("Alarm: where '%s' did not match regexp." % alarm_dict['alarm_where'])
            continue
        servername = res.group(1)
        targetname = res.group(2)

        obuffer = False
        servers = wcb.weechat.infolist_get("irc_server", "", "")
        while wcb.weechat.infolist_next(servers):
            this_server = wcb.weechat.infolist_string(servers, 'name')
            if servername != this_server:
                continue
            obuffer = wcb.weechat.infolist_pointer(servers, 'buffer')
        wcb.weechat.infolist_free(servers)

        if not obuffer:
            wcb.mlog("Alarm '%s' for '%s' in '%s': lookup for '%s' yielded no buffer." %
                (alarm_dict['alarm_text'], alarm_dict['alarm_who'], alarm_dict['alarm_where'], servername))
            return wcb.weechat.WEECHAT_RC_OK

        do_save = 1
        msg = "%s, time for your alarm: %s" % (alarm_dict['alarm_who'], alarm_dict['alarm_text'])
        wcb.weechat.command(obuffer, "/msg %s %s" % (targetname, msg))
        wcb.mlog("Sent alarm '%s' for '%s'(%s) in '%s' at '%s'!" %
            (alarm_dict['alarm_text'], alarm_dict['alarm_who'], targetname, alarm_dict['alarm_where'], servername))

    wcb.alarms = new_alarms
    if do_save:
        wcb.save_obj_as_json(wcb.alarms, wcb.state['bot_alarms'])
    return wcb.weechat.WEECHAT_RC_OK


def run(wcb, event):
    if event['signal'] == 'timer_signal':
        return alarm_timer_event(wcb, event)

    if event['command'] == 'alarm-del':
        return alarm_del(wcb, event)

    if event['command_args'] == '' or event['command'] == 'alarm-list':
        return alarm_list(wcb, event)
    alarm_add(wcb, event)
