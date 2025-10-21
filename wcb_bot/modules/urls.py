import html
import time
import gzip
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
    auto_urls_trigger = False
    manual_urls_trigger = False

    # See if url can be matched.
    res = wcb.re.search(r"(?i)(https?\:\/\/[a-z0-9\-\_]+\.[a-z0-9\-\.\_]+(?:\/[^\s]+)*[^\s])", event['text'])
    if res:
        url = res.group(1)
        if '..' in url:
            return wcb.signal_cont # #lazy fix for regexp catching "bla..." as url

        # music.youtube.com URLs only give 'Upgrade your browser'-titles in contrast to www.youtube.com urls
        # silently rewrite
        if 'music.youtube' in url:
            url = url.replace('music.youtube', 'www.youtube')

        if urls[channel]['url'] != url:
            urls[channel]['url'] = url
            urls[channel]['info'] = {}
            urls[channel]['updated'] = 0
            auto_urls_trigger = True

    if 'auto_urls_channels' not in wcb.state or channel not in wcb.state['auto_urls_channels']:
        auto_urls_trigger = False

    if wcb.re.match(wcb.state['bot_trigger_re'] + '@', event['text']):
        manual_urls_trigger = True

    if not manual_urls_trigger and not auto_urls_trigger:
        return wcb.signal_cont

    rtxt_postfix = ''
    last_url = urls[channel]['url']
    last_upd = urls[channel]['updated']
    if ' -f' in event['text']: last_upd = 0
    ttl = 300 - (int(time.time()) - int(last_upd))
    if ttl < 0:
        try:
            urls[channel]['info'] = fetchURLinfo(wcb, last_url)
            urls[channel]['updated'] = int(time.time())
        except Exception as e:
            wcb.say("URL info error: '%s'" % e)
            return wcb.signal_stop
    else:
        rtxt_postfix = "(cached,ttl:%ds)" % ttl

    if 'text/html' not in urls[channel]['info']['content-type']:
        rtxt_postfix += "|| (%s, %s) " % (urls[channel]['info']['content-type'], urls[channel]['info']['encoding'])
    if ' -f' in event['text']:
        rtxt_postfix += "(url: %s)" % last_url

    wcb.say("URL info: %s %s" % (urls[channel]['info']['title'], rtxt_postfix))
    return wcb.signal_stop


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
    if not wcb.re.match(r"^https?://", url):
        url = 'https://' + url

    req_headers = [
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Language: en-US,en;q=0.6',
        'Accept-Encoding: gzip',
    ]

    b = BytesIO() 
    c = pycurl.Curl() 
    c.setopt(c.URL, url)
    c.setopt(c.FOLLOWLOCATION, 1)
    c.setopt(c.CONNECTTIMEOUT, 4)
    c.setopt(c.TIMEOUT, 4)
    c.setopt(c.MAXREDIRS, 5)
    c.setopt(c.USERAGENT, 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    c.setopt(pycurl.HTTPHEADER, req_headers)
    c.setopt(c.WRITEFUNCTION, b.write)
    c.setopt(c.HEADERFUNCTION, __pycurl_headerfn)
    c.perform() 
    c.close()

    encoding = None
    if 'content-type' in headers:
        content_type = headers['content-type'].lower()
        res = wcb.re.search(r'charset=(\S+)', content_type)
        if res:
            encoding = res.group(1)
    if encoding is None:
        encoding = 'utf8'
    elif encoding == 'binary':
        return {'title': 'binary data', 'encoding': encoding, 'content-type': content_type}

    if content_type:
        content_type = wcb.re.sub(r';.*', '', content_type)
    else:
        content_type = 'undef'

    body = b.getvalue()
    b.close()

    try:
        nbody = gzip.decompress(body)
        body = nbody
    except Exception as err:
        pass

    try:
        body = body.decode(encoding)
    except Exception as err:
        wcb.say("Error decoding HTTP response: %s" % err)
        return {'title': '', 'encoding': '', 'content-type': ''}

    title = '[title tag not found]'
    res = wcb.re.search(r'(?ims)<title[^>]*>(.+?)<\/title', body)
    if res:
        title = html.unescape(res.group(1))
        title = wcb.re.sub(r'^\\s+', ' ', title, flags=wcb.re.MULTILINE).strip()
        title = wcb.re.sub(r'[\r\n]', '', title, flags=wcb.re.MULTILINE).strip()

    return {'title': title, 'encoding': encoding, 'content-type': content_type}
