import psycopg2
import MySQLdb

dbi_h = 'services.freshdot.net'
dbi_u = 'irssibot'
dbi_p = 'x'
dbi_d = 'irssibot'

dbo_h = 'localhost'
dbo_u = 'weechatbot'
dbo_p = 'y'
dbo_d = 'weechatbot'

dbi = MySQLdb.connect(user = dbi_u, passwd = dbi_p, host = dbi_h, db = dbi_d)
dbi_cur = dbi.cursor()

dbo = psycopg2.connect(user = dbo_u, password = dbo_p, host = dbo_h, dbname = dbo_d)
dbo_cur = dbo.cursor()

#ib_users

#ib_hostmasks

#ib_perms

#ib_infoitems

#ib_quotes

#ib_karma
#ib_karma_who
#ib_karma_why


