import subprocess
import multiprocessing
import ast
import grpc
import p4_runtimes
import p4_read_topo
import p4_counter
import p4_read_table
import p4_write_table

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)    # 全分离跨域

# 添加路由和视图函数
@app.route("/")
def index():
    return render_template("index.html")

# 读拓扑结构
@app.route("/read_topo")
def read_topo():
    try:
        data = p4_read_topo.read_topo()
        return jsonify(data)
    except Exception as e:
        return str(e)
    
# 流量监控
@app.route("/send_probe")
def send_probe():
    command = "mx h1 python3 probe.py "
    e_port = "2,2,2,2,3,3,3,3,1"    # 探针路径
    try:
        process = subprocess.Popen(command + e_port, shell=True, text=True, 
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.wait(5)
        output = process.communicate()[0]
        # return output # 测试用
        start = output.index("{")
        end = output.rindex("}") + 1
        result = output[start:end]
        return jsonify(ast.literal_eval(result))
    except subprocess.TimeoutExpired as e:
        return "请求超时"
    except Exception as e:
        return str(e)

# 读取计数器
@app.route("/read_counter")
def read_counter():
    try:
        args = p4_runtimes.check_parser()
        p4info_helper, sws = p4_runtimes.sw_connection(args.p4info)
        data = p4_counter.read_counters(p4info_helper, sws)
        flag = True
    except grpc.RpcError as e:
        p4_runtimes.printGrpcError(e)
        flag = False
    except Exception as e:
        print(e)
        flag = False
    p4_runtimes.shut_down()
    if flag:
        return jsonify(data)
    else:
        return "查询计数器失败"

# 读取流表
@app.route("/read_table")
def read_tables():
    try:
        args = p4_runtimes.check_parser()
        p4info_helper, sws = p4_runtimes.sw_connection(args.p4info)
        data = p4_read_table.read_tables(p4info_helper, sws)
        flag = True
    except grpc.RpcError as e:
        p4_runtimes.printGrpcError(e)
        flag = False
    except Exception as e:
        print(e)
        flag = False
    p4_runtimes.shut_down()
    if flag:
        return jsonify(data)
    else:
        return "查询流表失败"
    
# 下发流表
@app.route("/write_table", methods=["POST"])
def write_tables():
    form_args = request.get_json()
    try:
        args = p4_runtimes.check_parser()
        p4info_helper, sws = p4_runtimes.sw_connection(args.p4info)
        p4_write_table.sw_set_P4(p4info_helper, args.bmv2_json, sws)
        p4_write_table.write_tables(p4info_helper, sws, form_args)
        flag = True
    except grpc.RpcError as e:
        p4_runtimes.printGrpcError(e)
        flag = False
    except Exception as e:
        print(e)
        flag = False
    p4_runtimes.shut_down()
    if flag:
        return "下发流表成功"
    else:
        return "下发流表失败"

# 创建子进程
def new_process(command):
    process = subprocess.Popen(command, shell=True, text=True, 
                               stdin=subprocess.PIPE, 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT)
    result = process.communicate()[0]
    while process.poll() is None:  # 进程未终止
            line = process.stdout.readline()
            result += line
    return result


if __name__ == "__main__":    
    try:
        # new_process("make clean")
        # run_p4_proc = multiprocessing.Process(target=new_process("make run"))
        # run_p4_proc.start()
        # print("mininet启动完成")
        
        # 修改文件权限
        new_process("sudo chmod -R 777 .")
        app.run(host="127.0.0.1", port=5555, debug=True, threaded=False)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
        
    # run_p4_proc.terminate()
    # print("mininet已停止")
    # new_process("make stop")
    # new_process("make clean")
    # print("缓存文件清理完成")
        