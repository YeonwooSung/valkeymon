import sys
import os

PORT_START = int(sys.argv[1])
PORT_END = int(sys.argv[2])
PID_PATH = sys.argv[3]


def read_sample(path):
    f = open(path)
    data = str(f.read())
    f.close()

    return data


def create_conf(data, port, pid_path, path):
    data_with_port = data.replace("{{port}}", str(port))
    data_fullconfig = data_with_port.replace("{{pid_path}}", pid_path)
    wf = open(path, "w")
    wf.write(data_fullconfig)
    wf.close()
    return True


if __name__ == "__main__":
    data = read_sample("./sample.conf")
    servers = []
    cwd = os.getcwd()
    for i in range(PORT_START, PORT_END+1):
        newname = f"{cwd}/{i}.conf"
        create_conf(data, i, PID_PATH, newname)
        servers.append(f"127.0.0.1:{i}")
        print(f"valkey-server {cwd}/{i}.conf")

    print("valkey-cli --cluster create " + " ".join(servers))
    print("valkey-cli --cluster add-node {primary} {replica} --cluster-slave")
