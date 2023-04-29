/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

const bit<16> TYPE_IPV4 = 0x800;
const bit<8> TYPE_TCP = 6;
const bit<19> ECN_THRESHOLD = 10;   // ecn阈值
const bit<16> TYPE_PROBE = 0x812;   // 探针

#define MAX_PHOPS 10    // 探针最多跳
#define MAX_PORTS 8     // 检测最多多端口

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;
typedef bit<32> qdepth_t;   // 队列深度
typedef bit<48> time_t; // 时间

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<6>    diffserv;
    bit<2>    ecn;      // ecn
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<3>  ecn;
    bit<6>  ctrl;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

// 探针头
header probe_t {
    bit<8>  hop_cnt;    // 探针经过跳数
}
header probe_data_t {   // 交换机在每跳添加到探针的数据
    bit<1>  bos;
    bit<7>  swid;
    bit<8>  port;
    qdepth_t  qdepth;
    bit<32> byte_cnt;
    time_t  last_time;
    time_t  cur_time;
}
header probe_fwd_t {
    bit<8>  egress_spec;// 探针转发端口
}
struct parser_metadata_t {
    bit<8>  remaining;
}

struct metadata {
    bit<8> egress_spec;
    parser_metadata_t parser_metadata;
    bit<14> ecmp_select;

}

struct headers {
    ethernet_t  ethernet;
    ipv4_t      ipv4;
    tcp_t       tcp;
    probe_t     probe;  // 探针
    probe_fwd_t[MAX_PHOPS]   probe_fwd;  // 最多 10 跳
    probe_data_t[MAX_PHOPS]  probe_data; // 最多 10 跳

}

/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {    
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            TYPE_PROBE: parse_probe;    // 转探针解析器
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            TYPE_TCP: parse_tcp;
            default: accept;
        }
    }
    state parse_tcp {
        packet.extract(hdr.tcp);
        transition accept;
    }

    
    state parse_probe {
        packet.extract(hdr.probe);
        meta.parser_metadata.remaining = hdr.probe.hop_cnt + 1;
        transition select(hdr.probe.hop_cnt) {
            0: parse_probe_fwd; // 第一跳, probe_data 空,转 parse_probe_fwd
            default: parse_probe_data;
        }
    }

    state parse_probe_data {
        packet.extract(hdr.probe_data.next);
        transition select(hdr.probe_data.last.bos) {
            1: parse_probe_fwd; // 解析到栈底,转 parse_probe_fwd
            default: parse_probe_data;  // 递归解析
        }
    }

    state parse_probe_fwd {
        packet.extract(hdr.probe_fwd.next);
        meta.parser_metadata.remaining = meta.parser_metadata.remaining - 1;
        // 解析下一跳端口
        meta.egress_spec = hdr.probe_fwd.last.egress_spec;
        transition select(meta.parser_metadata.remaining) {
            0: accept;  // 解析到栈底,接收
            default: parse_probe_fwd;   // 递归解析
        }
    }
}


/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    
    counter(1<<2, CounterType.packets_and_bytes) ipv4Counter;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        ipv4Counter.count((bit<32>) standard_metadata.ingress_port);
        ipv4Counter.count((bit<32>) standard_metadata.egress_spec);
    }

    // 计算hash值
    action set_ecmp_select(bit<16> ecmp_base, bit<32> ecmp_count) {
        hash(meta.ecmp_select,
            HashAlgorithm.crc16,
            ecmp_base,
            { hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr,
              hdr.ipv4.protocol,
              hdr.tcp.srcPort,
              hdr.tcp.dstPort },
            ecmp_count);
    }
    // 根据hash值转发
    action set_nhop(macAddr_t nhop_dmac, bit<9> port) {
        // hdr.ipv4.dstAddr = nhop_ipv4;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = nhop_dmac;
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        ipv4Counter.count((bit<32>) standard_metadata.ingress_port);
        ipv4Counter.count((bit<32>) standard_metadata.egress_spec);
    }

    // 探针转发
    action probe_forward() {
        standard_metadata.egress_spec = (bit<9>)meta.egress_spec;
        hdr.probe.hop_cnt = hdr.probe.hop_cnt + 1;
    }

    table ecmp_group {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            drop;
            set_ecmp_select;
        }
        size = 1024;
        default_action = drop();
    }

    table ecmp_nhop {
        key = {
            meta.ecmp_select: exact;
        }
        actions = {
            set_nhop;
            drop;
        }
        size = 1024;
        default_action = drop();
    }

    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            ipv4_forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = NoAction();
    }

    apply {
        if (hdr.probe.isValid()) {
            probe_forward();
        } else
        if (hdr.ipv4.isValid()) {
            if (!ipv4_lpm.apply().hit) {
                ecmp_group.apply(); // 计算hash值
                ecmp_nhop.apply();  // 根据hash值转发
            }
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {
    
    // 计算自上次探针以来看到的字节数
    register<bit<32>>(MAX_PORTS) byte_cnt_reg;
    // 计算自上次探针来的时间
    register<time_t>(MAX_PORTS) last_time_reg;

    action check_ecn() {
        if (hdr.ipv4.ecn == 1 || hdr.ipv4.ecn == 2){
            if (standard_metadata.enq_qdepth >= ECN_THRESHOLD){
                hdr.ipv4.ecn = 3;
            }
        }
    }

    action add_probe(bit<7> swid) {
        // 写探针
        hdr.probe_data.push_front(1);
        hdr.probe_data[0].setValid();
        if (hdr.probe.hop_cnt == 1) {
            hdr.probe_data[0].bos = 1;
        }
        else {
            hdr.probe_data[0].bos = 0;
        }
        // 设置交换机id
        hdr.probe_data[0].swid = swid; 
        // 写其他的探针
        hdr.probe_data[0].port = (bit<8>)standard_metadata.egress_port;
        hdr.probe_data[0].qdepth = (qdepth_t)standard_metadata.deq_qdepth;
    }

    table probe {
        actions = {
            add_probe;
            NoAction;
        }
        default_action = NoAction();
    }

    apply {
        bit<32> byte_cnt;
        bit<32> new_byte_cnt;
        time_t last_time;
        time_t cur_time = standard_metadata.egress_global_timestamp;    // 当前时间
        // 增加此数据包端口的字节
        byte_cnt_reg.read(byte_cnt, (bit<32>)standard_metadata.egress_port);
        byte_cnt = byte_cnt + standard_metadata.packet_length;
        // 当探针通过时重置字节计数
        new_byte_cnt = (hdr.probe.isValid()) ? 0 : byte_cnt;
        byte_cnt_reg.write((bit<32>)standard_metadata.egress_port, new_byte_cnt);

        if (hdr.probe.isValid()) {
            probe.apply();
            hdr.probe_data[0].byte_cnt = byte_cnt;
            // 读取更新时间寄存器
            last_time_reg.read(last_time, (bit<32>)standard_metadata.egress_port);
            last_time_reg.write((bit<32>)standard_metadata.egress_port, cur_time);
            hdr.probe_data[0].last_time = last_time;
            hdr.probe_data[0].cur_time = cur_time;
        }else
        if (hdr.ipv4.isValid()) {
            check_ecn();   // 检查ecn
        }
    }

}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
    
    apply {
        update_checksum(
            hdr.ipv4.isValid(),
            { hdr.ipv4.version,
              hdr.ipv4.ihl,
              hdr.ipv4.diffserv,
              hdr.ipv4.ecn, // ecn
              hdr.ipv4.totalLen,
              hdr.ipv4.identification,
              hdr.ipv4.flags,
              hdr.ipv4.fragOffset,
              hdr.ipv4.ttl,
              hdr.ipv4.protocol,
              hdr.ipv4.srcAddr,
              hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}


/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
        // 探针
        packet.emit(hdr.probe);
        packet.emit(hdr.probe_data);
        packet.emit(hdr.probe_fwd);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
