import re
import json
import pycurl
import urllib.parse
from io import BytesIO 


headers = {}


def config(wcb):
    if 'wolfram_appid' not in wcb.state:
        wcb.state['wolfram_appid'] = ''

    return {
        'events': [],
        'commands': ['wolfram', 'w', 'gcalc', 'calc', 'convert'],
        'permissions': ['user'],
        'help': "Ask mundane questions to Wolfram and display resolt."
    }


def run(wcb, event):
    if wcb.state['wolfram_appid'] == '':
        return wcb.say("Ask '%s' to configure 'wolfram_appid' first!" % (wcb.state['bot_ownermask']))

    converted = False
    args = event['command_args']
    if 'noconv' in args:
        args = re.sub(r'\s*noconv\s*', '', args)
    else:
        converted = True
        args = re.sub(r'([KMGTPEkmgtpe])([bB])', r'\1i\2', args)

    wolfram_url = "https://api.wolframalpha.com/v2/query?format=plaintext&output=JSON&appid=%s&input=%s"
    wolfram_url = wolfram_url % (wcb.state['wolfram_appid'], urllib.parse.quote(args, safe=''))

    query_result_json = fetchURL(wcb, wolfram_url)
    qr = json.loads(query_result_json)
    if not 'queryresult' in qr:
        return wcb.say("No query result was returned by Wolfram or error fetching results.")
    if not 'pods' in qr['queryresult']:
        return wcb.say("No result pods were returned by Wolfram or error fetching results.")

    res_input = res_result = None
    for pod in qr['queryresult']['pods']:
        if not 'id' in pod:
            continue
        if pod['id'] == 'Input':
            res_input = pod['subpods'][0]['plaintext']
        if pod['id'] == 'DecimalApproximation':
            res_result = pod['subpods'][0]['plaintext']
        if pod['id'] == 'Result':
            res_result = pod['subpods'][0]['plaintext']

    if not res_input or not res_result:
        #wcb.mlog("%s" % query_result_json)
        return wcb.say("Query not understood.")

    if converted:
        wcb.reply("query converted to use binary units: '%s' - put 'noconv' anywhere to prevent this." % args)
    return wcb.say("%s = %s" % (res_input, res_result))


def __pycurl_headerfn(header_line):
    header_line = header_line.decode('iso-8859-1')
    if ':' not in header_line:
        return
    h_name, h_value = header_line.split(':', 1)
    h_name = h_name.strip()
    h_value = h_value.strip()
    h_name = h_name.lower()
    headers[h_name] = h_value


def fetchURL(wcb, url):
    b = BytesIO() 
    c = pycurl.Curl() 
    c.setopt(c.URL, url)
    c.setopt(c.FOLLOWLOCATION, 1)
    c.setopt(c.MAXREDIRS, 5)
    c.setopt(c.MAXFILESIZE, 65536)
    c.setopt(c.USERAGENT, 'WeeChatBot Wolfram API module')
    c.setopt(c.WRITEFUNCTION, b.write)
    c.setopt(c.HEADERFUNCTION, __pycurl_headerfn)
    c.perform() 
    c.close()

    encoding = None
    if 'content-type' in headers:
        content_type = headers['content-type'].lower()
        res = wcb.re.search('charset=(\S+)', content_type)
        if res:
            encoding = res.group(1)
    if encoding is None:
        encoding = 'utf8'

    body = b.getvalue()
    b.close()

    try:
        body = body.decode(encoding)
    except Exception as err:
        wcb.say("Error decoding HTTP response: %s" % err)
        return {}

    return str(body)
