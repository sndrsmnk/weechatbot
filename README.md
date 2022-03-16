WeechatBot
====
This is an IRC bot implementation built with Weechat Python scripting.<br/>
(c) 2020 GPLv2+ - There may be dragons.

You may need some or all of these Ubuntu packages: weechat, python3-psycopg2, python3-pycurl, python3-iso3166

Disclaimer: i have no idea what i'm doing. This could be implemented much more betterer.

Quick install guide:
----
 * This needs a PostgreSQL database. Schema is in `$GITHOME/dbschema.psql`.

 * Create a new user '**weechatbot**' (or joe, polly or finnigan...)
 * Start weechat 2.8+, Python 3+, quit weechat. This creates ~/.weechat/

 * Checkout this repo in $HOME
```sh
$ cd $HOME
$ git clone https://github.com/sndrsmnk/weechatbot.git
```

 * Set some symlinks for Weechat:
```sh
$ ln -sf ~/weechatbot/wcb.py .weechat/python/wcb.py
$ ln -sf ~/weechatbot/wcb_bot .weechat/python/wcb_bot
$ ln -sf ~/.weechat/python/wcb.py ~/.weechat/python/autoload/wcb.py
```

 * Start Weechat, fix WeeChatBot loading errors by installing missing dependencies

 * Quit Weechat, edit `~/.weechat/python/wcb_bot/wcb_config.json` and update `db_*` info

 * Start Weechat, read the script output in WeeChatbot status window as it shows the '**unique id**' of the bot and how to claim ownership.
 * Set up Weechat as you would normally do, configure networks, servers, channels, specify auto{connect,join} etc.
   * `/script install autojoin.py`
   * `/server add someNetwork someServer.tld/port -autoconnect`
   * `/join #yourChannel`
   * `/autojoin --run`

 * Join IRC with your own client and claim the bot, use !help, **read the source** and remember that i didn't write this for you, i wrote this for me. ;)

 * I would advise to take care with other plugins and this bot, they may clash.
 * You might want to disable Weechat's flood protection features if you plan to use the UDP listener a lot.


UDP listener
----
To configure the UDP-listener, you may need to set some configuration options after the bot was claimed. A module named 'set' can be used by the owner to set (almost) any value in the bot's state hash:

```text
!set udp_listen_ip ::ffff:127.0.0.1
!set udp_listen_port 47774
!set udp_listen_pass s00p3rzeeKRiT!
```

**NOTE**: The ```udp_listen_ip``` **must** be specified in IP6 notation. Prepend ```::ffff:``` to IPv4 addresses if used.

After changing these values, use the ```!udp-reopen``` command to re-open ('restart') the UDP-listener.<br/>
Use the ```!save``` command to make the configuration permanent.

You can now send UDP-datagrams to the IP and port specified to have the bot output them on IRC:
```sh
$ echo "s00p3rzeeKRiT! #testchan Test message via UDP" | nc -q1 -u 127.0.0.1 47774
```
If the bot is on multiple networks with the same channelname, you can specify the Weechat network name to help the bot decide where to output the message:
```sh
$ echo "s00p3rzeeKRiT! ircnet #testchan Test message on ircnet via UDP" | nc -q1 -u 127.0.0.1 47774
```

