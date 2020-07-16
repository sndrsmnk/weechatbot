import html
import time
import pycurl
from io import BytesIO 

headers = {}

def config(wcb):
    if 'urls' not in wcb.state:
        wcb.state['urls'] = {}

    return {
        'events': ['irc_in2_PRIVMSG'],
        'commands': ['@'],
        'permissions': ['user'],
        'help': "Keeps track of URLs and fetches info for them."
    }


def run(wcb, event):
    channel = event['channel']
    urls = wcb.state['urls']
    # Environmental sanity
    if channel not in urls:
        urls[channel] = {'url': '', 'info': '', 'updated': 0}

    # See if url can be matched.
    res = wcb.re.search("((?:https?\:\/\/)?[a-z0-9\-\_]+\.[a-z0-9\-\.\_]+(?:\/[^\s]+)*[^\s])", event['text'])
    if res:
        url = res.group(1)
        if '..' in url:
            return # #lazy fix for regexp catching "bla..." as url
        if urls[channel]['url'] != url:
            urls[channel]['url'] = url
            urls[channel]['info'] = {}
            urls[channel]['updated'] = 0

    # Exit early if event does not match the trigger regexp.
    if not wcb.re.match(wcb.state['bot_trigger_re'], event['text']):
        return
    # Strip off bot_trigger_re from text
    event_text = wcb.re.sub(wcb.state['bot_trigger_re'], '', event['text'])
    # Exit early if not our trigger.
    if not event_text.startswith('@'):
        return
        
    rtxt_postfix = ''
    last_url = urls[channel]['url']
    last_upd = urls[channel]['updated']
    if '-f' in event_text: last_upd = 0
    ttl = 300 - (int(time.time()) - int(last_upd))
    if ttl < 0:
        urls[channel]['info'] = fetchURLinfo(wcb, last_url)
        urls[channel]['updated'] = int(time.time())
    else:
        rtxt_postfix = "(cached,ttl:%ds)" % ttl
    if '-f' in event_text: rtxt_postfix += "(url: %s)" % last_url

    return wcb.say("URL info: %s || (%s, %s) %s" % (urls[channel]['info']['title'], urls[channel]['info']['content-type'], urls[channel]['info']['encoding'], rtxt_postfix))


def __pycurl_headerfn(header_line):
    header_line = header_line.decode('iso-8859-1')
    if ':' not in header_line:
        return
    h_name, h_value = header_line.split(':', 1)
    h_name = h_name.strip()
    h_value = h_value.strip()
    h_name = h_name.lower()
    headers[h_name] = h_value


def fetchURLinfo(wcb, url):
    if not wcb.re.match("^https?://", url):
        url = 'https://' + url

    b = BytesIO() 
    c = pycurl.Curl() 
    c.setopt(c.URL, url)
    c.setopt(c.FOLLOWLOCATION, 1)
    c.setopt(c.MAXREDIRS, 5)
    c.setopt(c.MAXFILESIZE, 65536)
    c.setopt(c.USERAGENT, 'Mozilla')
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
        wcb.mlog("Found content-type charset '%s'" % encoding)
    if encoding is None:
        encoding = 'utf8'
        wcb.mlog("Assuming encoding is '%s'" % encoding)
    elif encoding == 'binary':
        return {'title': 'binary data', 'encoding': encoding, 'content-type': content_type}

    if content_type:
        content_type = wcb.re.sub(';.*', '', content_type)
    else:
        content_type = 'undef'

    body = b.getvalue()
    b.close()

    try:
        body = body.decode(encoding)
    except Exception as err:
        wcb.say("Error decoding HTTP response: %s" % err)
        return {'title': '', 'encoding': '', 'content-type': ''}

    title = '[title tag not found]'
    res = wcb.re.search('<title[^>]*>(.+?)<\/title', body)
    if res:
        title = html.unescape(res.group(1))

    return {'title': title, 'encoding': encoding, 'content-type': content_type}
