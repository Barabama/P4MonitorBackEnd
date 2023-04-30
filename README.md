# P4MonitorBackEnd

这是一个基于P4的拓扑链路监控的后端项目

## 环境部署

- P4实验环境下载地址

```
https://github.com/jafingerhut/p4-guide/blob/master/bin/README-install-troubleshooting.md
```

- P4-Utils

```
https://github.com/nsg-ethz/p4-utils
```

## 项目部署

```bash
# 项目部署在与tutorials同一目录
cd ~
git clone https://github.com/Barabama/P4MonitorBackEnd.git
```

```bash
# 启动P4
cd ~/P4MonitorBackEnd
make run
```

```bash
# 新建终端启动flask
cd ~/P4MonitorBackEnd
python3 app.py
```
