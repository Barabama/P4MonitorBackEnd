#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import probe
from scapy.all import *

def handle_pkt(pkt):
    print("got a packet")
    # pkt.show2()
    if Raw in pkt:
        raw_layers = pkt[Raw]
        raw_content = raw_layers.load
        print("content: {}".format(raw_content))
    sys.stdout.flush()
    
def receive(iface):
    print("sniffing on {}".format(iface))
    sniff(iface = iface, prn = lambda x: handle_pkt(x))

if __name__ == '__main__':
    iface = probe.get_if()
    receive(iface)