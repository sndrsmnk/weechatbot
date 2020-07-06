#!/usr/bin/python3
# WeeChatBot (WCB), ©2020 Sander Smeenk <github@freshdot.net>
#
SN = 'wcb'
SA = 'Sander Smeenk <github@freshdot.net>'
SV = '0.1'
SL = 'GPLv3'
SD = 'Pluggable WeeChat IRC bot'
import sys
sys.dont_write_bytecode = True

import weechat
import wcb_bot as wcb

# Shims for hooking to WeeChatBot-Class functions
def shim_wcb_handle_buffer_input(data, buffer, input_data):
    return bot.wcb_handle_buffer_input(data, buffer, input_data)

def shim_wcb_handle_event(data, signal, signal_data):
    return bot.wcb_handle_event(data, signal, signal_data)

def shim_wcb_unload():
    return bot.wcb_unload()

def shim_wcb_handle_udp_input(data, fd):
    return bot.wcb_handle_udp_input(data, fd)


# Init!
if __name__ == '__main__' and weechat.register(SN, SA, SV, SL, SD, 'shim_wcb_unload', 'UTF-8'):
    bot = wcb.WeeChatBot(weechat)
