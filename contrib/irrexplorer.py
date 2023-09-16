#! /usr/bin/env python3

"""
Query IRRExplorer for routing information on an IP or prefix.

Written by Teun Vink <teun AT teun DOT tv>
"""

import requests
from netaddr import IPNetwork

def config(wcb):
    return {
        "events": [],
        "commands": ["irr", "irrexplorer"],
        "permissions": ["user"],
        "help": ["Show IRRExplorer information for a prefix"],
    }

def _print_items(wcb, results, status):
    """
    Fancy output for statuses.
    """
    STATUS = {
        "success": "\0039OK\003\002\002",
        "danger": "\0034ERROR\003\002\002",
        "warning": "\0038WARNING\003\002\002",
        "info": "\00312INFO\003\002\002",
    }

    for prefix in results.get(status, []):
        for msg in results[status][prefix]:
            wcb.say(f"[{STATUS[status]}] {prefix}: {msg}")


def run(wcb, event):
    net = event["command_args"]
    try:
        # typecast to IPNetwork so we know it's a valid IP or prefix
        IPNetwork(net)
    except Exception:
        return wcb.say(f"{net} is not a valid IP or prefix.")

    req = requests.get(f"https://irrexplorer.nlnog.net/api/prefixes/prefix/{net}")
    # check results
    if req.status_code != 200:
        return wc.say(f"Failed to query IRRExplorer: {req.text}")
    try:
        data = req.json()
    except Exception:
        return wcb.say("Failed to parse IRRExplorer answer.")

    # sort the results by category and prefix
    results = {}
    for item in data:
        pfx = f"{item['prefix']}"
        if len(item.get("bgpOrigins", [])) > 0:
            origins = ", ".join([f"AS{asn}" for asn in item["bgpOrigins"]])
            pfx = f"{pfx} ({origins})"
        for message in item["messages"]:
            cat = message["category"]
            if cat not in results:
                results[cat] = {pfx: []}
            if pfx not in results[cat]:
                results[cat][pfx] = []
            results[cat][pfx].append(message["text"])

    # always print these categories
    for status in ["success", "danger", "warning"]:
        _print_items(wcb, results, status)

    # some prefixes have MANY info items, only print them if there are 3 or less
    infoitems = results.get("info", {})
    infocount = sum([len(infoitems[p]) for p in infoitems])
    if infocount <= 3:
        _print_items(wcb, results, "info")
    else:
        wcb.say("Too many 'info' items found, not showing them here.")

    # print some details
    return wcb.say(f"More details: https://irrexplorer.nlnog.net/prefix/{net}")


