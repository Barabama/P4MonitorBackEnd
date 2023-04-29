#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import grpc

# 从 util 导入 P4Runtime_lib
sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "../tutorials/utils/"))
import p4runtime_lib.bmv2
import p4runtime_lib.helper
from p4runtime_lib.switch import ShutdownAllSwitchConnections

def check_parser():
    parser = argparse.ArgumentParser(description="P4Runtime Controller")
    parser.add_argument("--p4info", help="p4info proto in text format from p4c",
                        type=str, action="store", required=False,
                        default="./build/LinkMonitor.p4.p4info.txt")
    parser.add_argument("--bmv2-json", help="BMv2 JSON file from p4c",
                        type=str, action="store", required=False,
                        default="./build/LinkMonitor.json")
    args = parser.parse_args()

    if not os.path.exists(args.p4info):
        parser.print_help()
        print("\np4info 未找到: {}\n使用命令'make'后重试".format(args.p4info))
        parser.exit(1)
    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        print("\nBMv2 JSON 未找到: {}\n使用命令'make'后重试".format(args.bmv2_json))
        parser.exit(1)
    return args

def sw_connection(p4info_file_path):
    # 从 p4info 文件实例化 P4Runtime 帮助程序
    p4info_helper = p4runtime_lib.helper.P4InfoHelper(p4info_file_path)

    # 创建交换机连接对象,由 P4Runtime gRPC 连接提供支持
    # 转储所有发送到切换到给定 txt 文件的 P4Runtime 消息
    switches = [
        {"name": "s1", "address": "127.0.0.1:50051", "device_id": 0, "proto_dump_file": "logs/s1-p4runtime-requests.txt"},
        {"name": "s2", "address": "127.0.0.1:50052", "device_id": 1, "proto_dump_file": "logs/s2-p4runtime-requests.txt"},
        {"name": "s3", "address": "127.0.0.1:50053", "device_id": 2, "proto_dump_file": "logs/s3-p4runtime-requests.txt"},
        {"name": "s4", "address": "127.0.0.1:50054", "device_id": 3, "proto_dump_file": "logs/s4-p4runtime-requests.txt"},

    ]
    sws = [p4runtime_lib.bmv2.Bmv2SwitchConnection(
        name=switch["name"], address=switch["address"], 
        device_id=switch["device_id"], proto_dump_file=switch["proto_dump_file"]
    ) for switch in switches
    ]
    for sw in sws:
        # 发送主仲裁更新消息以将此控制器建立为主控制器(P4Runtime 要求这执行在任何其他写入操作之前)
        sw.MasterArbitrationUpdate()
        print("{} 与 P4Runtime 建立连接".format(sw.name))
    return p4info_helper, sws

def sw_set_P4(p4info_helper, bmv2_file_path, sws):
    for sw in sws:
        # 在交换机上安装 P4 程序
        sw.SetForwardingPipelineConfig(p4info=p4info_helper.p4info, bmv2_json_file_path=bmv2_file_path)
        print("{} 已更新P4程序".format(sw.name))
        
def printGrpcError(e):
    print("gRPC Error:{}".format(e.details()), end=" ")
    status_code = e.code()
    print("({})".format(status_code.name), end=" ")
    traceback = sys.exc_info()[2]
    print("[{}:{}]".format(traceback.tb_frame.f_code.co_filename, traceback.tb_lineno))

def shut_down():
    ShutdownAllSwitchConnections()
    print("交换机与 P4Runtime 连接已断开")


if __name__ == "__main__":
    args = check_parser()
    try:
        sw_connection(args.p4info)
    except grpc.RpcError as e:
        printGrpcError(e)
    shut_down()

