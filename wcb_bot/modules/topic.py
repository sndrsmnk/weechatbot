def config(wcb):
    if 'previous_topic' not in wcb.state:
        wcb.state['previous_topic'] = {}

    return {
        'events': ['irc_in_TOPIC'],
        'commands': ['previous-topic', 'pt', 'topic-add', 'topic-del', 'topic-set'],
        'permissions': ['user'],
        'help': "Sets topic, queries previous topic."
    }


def run(wcb, event):
    # Find the previous topic for the channel!
    infolist = wcb.weechat.infolist_get('irc_channel', '', event['server'])
    while wcb.weechat.infolist_next(infolist):
        channel_name = wcb.weechat.infolist_string(infolist, 'name')
        if channel_name != event['channel']:
            continue
        modes = wcb.weechat.infolist_string(infolist, 'modes')
        topic = wcb.weechat.infolist_string(infolist, 'topic')
    wcb.weechat.infolist_free(infolist)


    if event['signal'] == 'irc_in_TOPIC':
        if not topic:
            return wcb.mlog("Lookup of topic on '%s' yielded no value.")
        wcb.state['previous_topic'][event['channel']] = topic
        return wcb.signal_cont


    if wcb.re.match("^(?:pt|previous-topic)$", event['command']):
        if event['channel'] not in wcb.state['previous_topic']:
            return wcb.say("No topic information on '%s' was saved yet." % event['channel'])
        return wcb.say("Previous topic on '%s' was '%s'" % (event['channel'], wcb.state['previous_topic'][event['channel']]))


    # All functions below, require the bot to be op, or channel mode to be -t.
    if not event['bot_is_op'] and 't' in modes:
            return wcb.say("I am not op, and channel mode is +t. Sorry.")


    if event['command'] == 'topic-set':
        new_topic = event['command_args']
        if new_topic == '':
            return wcb.reply("topic-set what, exactly?")
        wcb.state['previous_topic'][event['channel']] = topic
        wcb.weechat.command(event['weechat_buffer'], '/topic ' + new_topic)
        return wcb.signal_cont


    if event['command'] == 'topic-add':
        add_topic = event['command_args']
        if add_topic == '':
            return wcb.reply("topic-add what, exactly?")
        new_topic = topic + ' | ' + add_topic
        wcb.state['previous_topic'][event['channel']] = topic
        wcb.weechat.command(event['weechat_buffer'], '/topic ' + new_topic)
        return wcb.signal_cont


    if event['command'] == 'topic-del':
        del_topic_elem_idx = event['command_args']
        if del_topic_elem_idx == '' or not del_topic_elem_idx.isnumeric():
            return wcb.reply("topic-del requires a positive integer index argument where 1 is the first element of the topic.")
        del_topic_elem_idx = int(del_topic_elem_idx) - 1

        topic_elems = topic.split(' | ')
        if del_topic_elem_idx > len(topic_elems):
            return wcb.reply("topic element index '%d' > '%s'" % (del_topic_elem_idx, len(topic_elems)))

        del topic_elems[del_topic_elem_idx]
        new_topic = ' | '.join(topic_elems)
        wcb.state['previous_topic'][event['channel']] = topic
        wcb.weechat.command(event['weechat_buffer'], '/topic ' + new_topic)
        return wcb.signal_cont
