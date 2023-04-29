#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
from p4_runtimes import *

# 读取交换机的流规则
def read_table(p4info_helper, sw):
    print("\n----- 正在读取 {} 的流规则 -----".format(sw.name))
    for response in sw.ReadTableEntries():
        entities =[]
        for entity in response.entities:
            entry = entity.table_entry
            table_entries = {}
            # table_name 为表名
            table_name = p4info_helper.get_tables_name(entry.table_id)
            # 写入表名
            print("{}: ".format(table_name))
            table_entries.update({"table": table_name})
            
            for mch in entry.match:
                # field 为匹配的键
                field = p4info_helper.get_match_field_name(table_name, mch.field_id)
                # key 为匹配的值
                key = list(p4info_helper.get_match_field_value(mch))
                print(key)
                if len(key) == 2:   # byte 转 str
                    key[0] = socket.inet_ntoa(key[0])
                elif len(key) == 1: # byte 转 int
                    key = int(key[0])
                # 写入匹配的键值对
                print(" {}: {} ->".format(field,key))
                table_entries.update({"match":{field: key}})
            
            # action_name 为动作名
            action = entry.action.action
            action_name = p4info_helper.get_actions_name(action.action_id)
            # 写入动作名
            print("  {}".format(action_name))
            table_entries.update({"action_name": action_name})
            
            action_params = {}
            for prms in action.params:
                # param_name 为动作参数键
                param_name = p4info_helper.get_action_param_name(action_name, prms.param_id)
                # param_value 为动作参数值
                param_value = prms.value
                if len(param_value) == 6:   # mac 转 str
                    param_value = ':'.join(['{:02x}'.format(b) for b in param_value])
                elif len(param_value) == 4: # ipv4 转 str
                    param_value = socket.inet_ntoa(param_value)
                elif len(param_value) ==1:  # byte 转 int
                    param_value = param_value[0]
                # 写入动作参数
                print("   {}: {}".format(param_name, param_value ))
                action_params.update({param_name: param_value})
            # 写入动作参数组
            table_entries.update({"action_params":action_params})
            # 写入这个流表项
            entities.append(table_entries)    
    print("-----  {} 的流规则读取完毕 -----".format(sw.name))
    return entities
    
def read_tables(p4info_helper, sws):
    sws_tables = {}
    for sw in sws:    
        # 读取交换机的流规则
        table_rules = read_table(p4info_helper=p4info_helper, sw=sw)
        sws_tables.update({sw.name: table_rules})
    return sws_tables


if __name__ == "__main__":
    args = check_parser()
    try:
        p4info_helper, sws = sw_connection(args.p4info)
        read_tables(p4info_helper, sws)
    except grpc.RpcError as e:
        printGrpcError(e)
    shut_down()
