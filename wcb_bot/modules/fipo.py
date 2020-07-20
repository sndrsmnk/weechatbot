import time
import sqlite3
from datetime import date as dateobj


def config(wcb):
    return {
        'events': [],
        'commands': ['fipo', 'fipostats', 'fiporeset', 'fiposet', 'setfipo'],
        'permissions': ['user'],
        'help': "Scores you that sweet-sweet fipo fame!"
    }


def run(wcb, event):
    fdb_file = "%s/module_fipo.sqlite3" % wcb.state['bot_base']
    fdb = sqlite3.connect(fdb_file)

    cur = fdb.cursor()
    sql = """CREATE TABLE IF NOT EXISTS fipo (
                date VARCHAR(8),
                channel TEXT,
                username TEXT,
                UNIQUE(date, channel)
            )"""
    cur.execute(sql)
    fdb.commit()

    if event['command'] == 'fipo':
        today = dateobj.today()
        todaystr = today.strftime("%Y%m%d")

        sql = "SELECT username FROM fipo WHERE date = ?"
        sql_arr = [todaystr]
        if not wcb.state['bot_shared_knowledge']:
            sql += " AND channel = ?"
            sql_arr.append(event['channel'])
        cur.execute(sql, sql_arr)
        res = cur.fetchone()
        if not res:
            sql = "INSERT INTO fipo (date, channel, username) VALUES (?, ?, ?)"
            cur.execute(sql, (todaystr, event['channel'], event['user_info']['username']))
            fdb.commit()
            return wcb.say("w00t! :D")

        if res[0] == event['user_info']['username']:
            return wcb.say("Yes! :D  It was YOU!  YOU SCORED TODAY'S FIPO!!  \\o/")


    if event['command'] == 'fiposet' or event['command'] == 'setfipo':
        if not wcb.perms('owner'): return
        if ' ' not in event['command_args']:
            return wcb.say("Usage: fiposet yyyymmdd dbusername")
        date, nick = event['command_args'].split(" ")
        if not date.isnumeric():
            return wcb.say("Usage: fiposet yyyymmdd dbusername")
        db_user = wcb.db_get_userinfo_by_username(nick)
        if not db_user:
            return wcb.reply("a user named '%s' was not found." % nick)
        sql = "INSERT INTO fipo (date, channel, username) VALUES (?, ?, ?) ON CONFLICT (date, channel) DO UPDATE SET username = ?"
        cur.execute(sql, (date, event['channel'], nick, nick))
        fdb.commit()
        return wcb.say("Fipo for %s set to '%s'" % (date, nick))


    if event['command'] == 'fiporeset':
        if not wcb.perms('owner'): return
        sql_arr = []
        sql = "DELETE FROM fipo"
        if not wcb.state['bot_shared_knowledge']:
            sql_arr.append(event['channel]'])
            sql += "WHERE channel = ?"
        cur.execute(sql, sql_arr)
        fdb.commit()
        return wcb.say("Fipo has been reset.")


    if event['command'] == 'fipostats':
        lookup_username = event['command_args']

        sql_arr = []
        sql = "SELECT date, username FROM fipo"
        if not wcb.state['bot_shared_knowledge']:
            sql_arr.append(event['channel'])
            sql += " WHERE channel = ?"
        sql += " ORDER BY date ASC"
        cur.execute(sql, sql_arr)
        rows = cur.fetchall()
        if not rows:
            return wcb.say("No fipo's yet! Quick!!")

        fipo_stats = {}
        last_username = ''
        streak = 0
        winning_streak = 0
        winning_streak_usernames = []

        for row in rows:
            date, username = row[0], row[1]

            if username not in fipo_stats:
                fipo_stats[username] = 1
            else:
                fipo_stats[username] += 1

            if username == last_username:
                streak += 1
                streak_username = username

            else:
                if streak > winning_streak:
                    winning_streak = streak
                    winning_streak_usernames = [last_username]
                elif streak == winning_streak:
                    if username not in winning_streak_usernames:
                        winning_streak_usernames.append(last_username)
                streak = 1
                streak_username = username
                last_username = username

        # check again at end of loop. streak might be 'in progress'... 
        if streak > winning_streak:
            winning_streak = streak
            winning_streak_usernames = [ username ]
        elif streak == winning_streak:
            if username not in winning_streak_usernames:
                winning_streak_usernames.append(username)

        if lookup_username:
            if lookup_username not in fipo_stats:
                return wcb.say("%s has not scored any fipo's yet." % lookup_username)

            if lookup_username == event['nick']:
                rtxt = "You "
            else: 
               rtxt = "%s " % lookup_username
            rtxt += "scored %d fipo's!" % fipo_stats[lookup_username]
            return wcb.say(rtxt)
        
        wcb.say("Longest streak of %d day(s) by %s" % (winning_streak, ", ".join(winning_streak_usernames)))

        r_arr = []
        display_count = 0
        # Sort dict keys by value
        for nick, fipocount in sorted(fipo_stats.items(), key=lambda item: item[1], reverse=True):
            display_count += 1
            out_nick = nick[0]
            out_nick += "\0030\003\002\002"
            out_nick += nick[1:]
            r_arr.append("%s(%s)" % (out_nick, fipocount))
            if display_count == 5:
                break

        return wcb.say("Top %d FIPO'ers: %s" % (display_count, ", ".join(r_arr)))
