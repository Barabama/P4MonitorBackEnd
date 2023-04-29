#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
import sys
import socket
from scapy.all import *
from probe import *

def send(iface):
    for i in range(10):
        pkt =  scapy.all.Ether(src=get_if_hwaddr(iface), dst='ff:ff:ff:ff:ff:ff')
        pkt = pkt / scapy.all.IP(dst=addr) / \
        scapy.all.TCP(dport=1234, sport=random.randint(49152,65535)) / str(i)
        # pkt.show2()
        sendp(pkt, iface=iface, verbose=False)
        time.sleep(0.5)
    pass

if __name__ == '__main__':
    if len(sys.argv)<2:
        print('pass 2 arguments: <destination>')
        exit(1)
    addr = socket.gethostbyname(sys.argv[1])
    iface = get_if()
    print("sending on interface {} to {}".format(iface, str(addr)))
    send(iface)