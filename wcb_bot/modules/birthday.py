import datetime
import psycopg2.extras
import re


def config(wcb):
    return {
        'events': [],
        'commands': ['bd-set', 'bd-del', 'birthday', 'birthdays', 'age', "jarig", "oud"],
        'permissions': ['user'],
        'help': "List, set and unset birthdays",
    }


def bd_set(wcb, event):
    args = event['command_args']
    re_ddmmyyyy = re.compile("^(\d{1,2})-(\d{1,2})-(\d{4})$")
    res = re.match(re_ddmmyyyy, args)
    if not res:
        return wcb.reply("usage 'bd-set dd-mm-yyyy'")

    dd = res.group(1)
    mm = res.group(2)
    yy = res.group(3)

    dob = "%d-%d-%d" % (int(yy), int(mm), int(dd))

    db = wcb.db_connect()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    sql = "UPDATE wcb_users SET dob = %s WHERE id = %s"
    cur.execute(sql, (dob, event['user_info']['id']))
    db.commit()

    sql = """SELECT
                EXTRACT(YEAR FROM AGE(dob)) AS year,
                EXTRACT(MONTH FROM AGE(dob)) AS month,
                EXTRACT(DAY FROM AGE(dob)) AS day
            FROM wcb_users WHERE id = %s"""
    cur.execute(sql, (event['user_info']['id'],))
    res = cur.fetchone()
    if not res:
        return wcb.say("Something went wrong. Oops!")
    age = "%d years, %d months and %d days" % (res['year'], res['month'], res['day'])
    return wcb.reply("set! That makes you %s young!" % age)


def bd_del(wcb, event):
    db = wcb.db_connect()
    cur = db.cursor()
    sql = "UPDATE wcb_users SET dob = NULL WHERE id = %s"
    cur.execute(sql, (event['user_info']['id'],))
    db.commit()
    return wcb.reply("your birthday info was removed.")


def show_age(wcb, event):
    lookup_uid = event['user_info']['id']
    arg = event['command_args']
    if arg and arg != '':
        target_hostmask = wcb.get_userhost_by_ircnick(arg)
        target_info = wcb.db_get_userinfo_by_userhost(target_hostmask)
        if not target_info or not target_info['id']:
            return wcb.reply("Can't find nick '%s' on this channel?" % (arg))
        lookup_uid = target_info['id']

    sql = """SELECT
                EXTRACT(YEAR FROM AGE(dob)) AS year,
                EXTRACT(MONTH FROM AGE(dob)) AS month,
                EXTRACT(DAY FROM AGE(dob)) AS day
            FROM wcb_users WHERE id = %s"""
    db = wcb.db_connect()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    cur.execute(sql, (lookup_uid,))
    res = cur.fetchone()
    if not res:
        return wcb.say("Something went wrong. Oops!")
    if not res['year']:
        return wcb.say('No birthday info known!')

    age = "You are"
    if lookup_uid != event['user_info']['id']:
        age = "%s is" % arg
    age += " %d years, %d months and %d days young!" % (res['year'], res['month'], res['day'])
    return wcb.say(age)


def show_birthdays(wcb, event):
    dt = datetime.datetime.now()
    dtt = dt.timetuple()
    nowmonth, nowday = (dtt[1], dtt[2])

    # BDs this month
    db = wcb.db_connect()
    cur = db.cursor(cursor_factory = psycopg2.extras.DictCursor)
    sql = """SELECT username, dob
            FROM wcb_users
            WHERE EXTRACT (MONTH FROM dob) = %s"""
    cur.execute(sql, (nowmonth,))
    res = cur.fetchall()
    if not res:
        return wcb.say("Something went wrong. Oops!")

    bdays = []
    for val in res:
        bdays.append("%s: %s" % (val['username'], val['dob']))

    if not len(bdays):
        return wcb.say("No (known) birthdays this month.")

    msg = "Birthdays this month: %s" % ", ".join(bdays)
    return wcb.say(msg)


def run(wcb, event):
    if event['command'] == 'bd-set':
        return bd_set(wcb, event)

    if event['command'] == 'bd-del':
        return bd_del(wcb, event)

    if event['command'] in ('age', 'oud'):
        return show_age(wcb, event)

    if event['command'] in ('birthday', 'birthdays', 'jarig'):
        return show_birthdays(wcb, event)

    return
