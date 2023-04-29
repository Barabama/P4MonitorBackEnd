#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from p4_runtimes import *


# 读取交换机的计数器
def read_counter(p4info_helper, sw):
    print("\n----- 正在读取 {} 的计数器 -----".format(sw.name))
    for response in sw.ReadCounters():
        counters = []
        for entity in response.entities:
            counter = entity.counter_entry
            counter_entries = {}
            counter_name = p4info_helper.get_counters_name(counter.counter_id)
            index = counter.index.index
            packet_count = counter.data.packet_count
            byte_count = counter.data.byte_count
            print("{} {}: {} packets ({} bytes)".format(counter_name, index, 
                                                        packet_count, byte_count))
            counter_entries.update({"port":index})
            counter_entries.update({"packets":packet_count})
            counter_entries.update({"bytes":byte_count})
            counters.append(counter_entries)
    print("-----  {} 的计数器读取完毕 -----".format(sw.name))
    return counters

def read_counters(p4info_helper, sws):
    sws_counters = {}
    for sw in sws:
        # 读取交换机计数器
        counters = read_counter(p4info_helper=p4info_helper, sw=sw)
        sws_counters.update({sw.name:counters})
    return sws_counters

if __name__ == "__main__":
    args = check_parser()
    try:
        p4info_helper, sws = sw_connection(args.p4info)
        read_counters(p4info_helper, sws)
    except grpc.RpcError as e:
        printGrpcError(e)
    shut_down()