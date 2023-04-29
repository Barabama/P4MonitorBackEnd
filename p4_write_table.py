#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from p4_runtimes import *

# 新增交换机 drop 流规则
def write_drop_rule(p4info_helper, sw):
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        default_action=True,
        action_name="MyIngress.drop",
        action_params={}
    )
    sw.WriteTableEntry(table_entry)
    print("{} 的 drop 流规则已生成".format(sw.name))
    
# 新增交换机 probe 流规则
def write_probe_rule(p4info_helper, sw, swid):
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyEgress.probe",
        action_name="MyEgress.add_probe",
        action_params={
            "swid": swid
        }
    )
    sw.WriteTableEntry(table_entry)
    print("{} 的 probe 流规则已生成".format(sw.name))

# 新增交换机 ipv4 流规则
def write_ipv4_rule(p4info_helper, sw, dst_ip_addr, ip_suffix, 
                     dst_eth_addr, forward_port):
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ipv4_lpm",
        match_fields={
            "hdr.ipv4.dstAddr": (dst_ip_addr, ip_suffix)
        },
        action_name="MyIngress.ipv4_forward",
        action_params={
            "dstAddr": dst_eth_addr,
            "port": forward_port
        }
    )
    sw.WriteTableEntry(table_entry)
    print(" {} 的 ipv4 流规则已生成: dst_ip={}, port={} "
          .format(sw.name, dst_ip_addr, forward_port))

# 新增 ecmp_group 流规则
def write_group_rule(p4info_helper, sw, dst_ip_addr, ip_suffix, 
                    #   dst_ip_mask, 
                      ecmp_base, ecmp_count):
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ecmp_group",
        match_fields={
            "hdr.ipv4.dstAddr": (dst_ip_addr, ip_suffix)
        },
        action_name="MyIngress.set_ecmp_select",
        action_params={
            # "dst_ip_mask": dst_ip_mask,
            "ecmp_base": ecmp_base,
            "ecmp_count": ecmp_count
        })
    sw.WriteTableEntry(table_entry)
    print("{} 的 ecmp group 流规则已生成: ({},{})"
          .format(sw.name, ecmp_base, ecmp_count))
    
# 新增 ecmp_nhop 流规则
def write_nhop_rule(p4info_helper, sw, ecmp_select, nhop_dmac, port):
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.ecmp_nhop",
        match_fields={
            "meta.ecmp_select": ecmp_select
        },
        action_name="MyIngress.set_nhop",
        action_params={
            "nhop_dmac": nhop_dmac,
            "port": port
        })
    sw.WriteTableEntry(table_entry)
    print("{} 的 ecmp nhop 流规则已生成: ecmp={}, port={}"
          .format(sw.name, ecmp_select, port))


def write_tables(p4info_helper, sws, args):
    with open("topo/flow_rules.json") as f:
        flow_rules = json.load(f)
    # 新增 drop 流表
    for rule in flow_rules["table_rules"]:
        write_drop_rule(p4info_helper=p4info_helper, sw=sws[rule["sw"]])
        
    for arg in args:
        if arg == "ipv4":
            # 新增 ipv4 流表
            for rule in flow_rules["ipv4_rules"]:
                write_ipv4_rule(p4info_helper=p4info_helper, sw=sws[rule["sw"]], 
                    dst_ip_addr=rule["dst_ip_addr"], ip_suffix=rule["ip_suffix"], 
                    dst_eth_addr=rule["dst_eth_addr"], forward_port=rule["forward_port"])


        elif arg == "ecmp":
            # 新增 ecmp_groups 流表
            for rule in flow_rules["ecmp_groups"]:
                write_group_rule(p4info_helper=p4info_helper, sw=sws[rule["sw"]], 
                                  dst_ip_addr=rule["dst_ip_addr"], ip_suffix=rule["ip_suffix"], 
                                  ecmp_base=rule["ecmp_base"], ecmp_count=rule["ecmp_count"])
            # 新增 ecmp_nhops 流表
            for rule in flow_rules["ecmp_nhops"]:
                write_nhop_rule(p4info_helper=p4info_helper, sw=sws[rule["sw"]], 
                                 ecmp_select=rule["ecmp_select"], 
                                 nhop_dmac=rule["nhop_dmac"], port=rule["port"])
        
        elif arg == "probe":
            # 新增 probe 流表            
            for rule in flow_rules["table_rules"]:
                write_probe_rule(p4info_helper=p4info_helper, 
                                  sw=sws[rule["sw"]], swid=rule["swid"])

if __name__ == "__main__":
    args = check_parser()
    try:
        p4info_helper, sws = sw_connection(args.p4info)
        sw_set_P4(p4info_helper, args.bmv2_json, sws)
        write_tables(p4info_helper, sws, ["probe","ipv4","ecmp"])
    except grpc.RpcError as e:
        printGrpcError(e)
    shut_down()
