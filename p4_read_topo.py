import json

def read_topo():
    data = {}
    with open("./topo/topology.json", "r") as f:
        topo = json.load(f)
        nodes = []
        edges = []
        i = 0
        for host in topo["hosts"].items():  
            i += 1
            nodes.append({
                "id": i,
                "label": host[0],
                "ip": host[1]["ip"],
                "mac": host[1]["mac"],
                "image": "imgPC",
                "shape": 'image'
            })
        for sw in topo["switches"]:
            i += 1
            nodes.append({
                "id": i,
                "label": sw,
                "image": "imgRouter",
                "shape": 'image'
            })
        for link in topo["links"]:
            for j in range(len(link)):
                if isinstance(link[j], str):
                    if link[j][0] == "h":
                        link[j] += "-eth0"
                    elif link[j][0] == "s":
                        link[j] = link[j].replace("p", "eth")
                elif isinstance(link[j], int):
                    pass 
            i += 1
            edges.append({
                "id": i,
                "from": link[0],
                "to": link[1]
            })
        data = {"nodes":nodes, "edges":edges}
    print(data)
    return data

if __name__ == "__main__":
    read_topo()