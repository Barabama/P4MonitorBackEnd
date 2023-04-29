#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import multiprocessing
from scapy.all import *

TYPE_PROBE = 0x812

class Probe(Packet):
   fields_desc = [ ByteField("hop_cnt", 0)]

class ProbeData(Packet):
   fields_desc = [ BitField("bos", 0, 1),
                   BitField("swid", 0, 7),
                   ByteField("port", 0),
                   IntField("qdepth", 0),   # 出队列深度
                   IntField("byte_cnt", 0),
                   BitField("last_time", 0, 48),
                   BitField("cur_time", 0, 48)]

class ProbeFwd(Packet):
   fields_desc = [ ByteField("egress_spec", 0)]

bind_layers(scapy.all.Ether, Probe, type=TYPE_PROBE)
bind_layers(Probe, ProbeFwd, hop_cnt=0)
bind_layers(Probe, ProbeData)
bind_layers(ProbeData, ProbeData, bos=0)
bind_layers(ProbeData, ProbeFwd, bos=1)
bind_layers(ProbeFwd, ProbeFwd)

def send_probe(iface, e_ports):
    probe_pkt = scapy.all.Ether(dst='ff:ff:ff:ff:ff:ff', src=get_if_hwaddr('eth0')) / \
                Probe(hop_cnt=0)
    for p in e_ports:
        try:
            probe_pkt = probe_pkt / \
            ProbeFwd(egress_spec=p)
        except ValueError:
            pass
    sendp(probe_pkt, iface=iface)

# 获取网卡端口
def get_if():
    ifs=get_if_list()
    iface=None
    for i in ifs:
        if "eth0" in i:
            iface=i
            break
    if not iface:
        print("Cannot find eth0 interface")
        exit(1)
    return iface

def expand(x):
    yield x
    while x.payload:
        x = x.payload
        yield x

# 收探针包
def handle_pkt(pkt):
    # pkt.show2()
    flow = {}
    qdepth = {}
    data = {
        "flow": flow,
        "qdepth": qdepth
    }
    global prev_time
    if prev_time is not None:
        # 发送到接收的时延
        data["delay"] = pkt.time - prev_time
    prev_time = pkt.time
    if ProbeData in pkt :
        data_layers = [l for l in expand(pkt) if l.name=='ProbeData']
        for sw in data_layers:
            if sw.cur_time == sw.last_time :
                utilization = 0 
            else :
                utilization = 8.0*sw.byte_cnt/(sw.cur_time - sw.last_time)
            # 链路流量
            if sw.port != 1:
                flow["s{}-eth{}".format(sw.swid, sw.port)] = utilization
            # 队列深度
            qdepth["s{}".format(sw.swid)] = sw.qdepth
        # print("Switch {} - Port {}: {} Mbps".format(sw.swid, sw.port, utilization))
        
        print(data)

def send_probes(e_ports):
    time.sleep(0.02)
    send_probe(iface, e_ports)


if __name__ == '__main__':
    iface = get_if()
    e_ports = eval(sys.argv[1])
    send_probe_proc = multiprocessing.Process(target=send_probes,args=(e_ports,))
    send_probe_proc.start()   # 多线程发包
    # print("sniffing on {}".format(iface))
    prev_time = None
    sniff(iface = iface, prn = lambda x: handle_pkt(x), 
          filter="ether proto 0x812", count = 2)
