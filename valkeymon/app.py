# -*- coding: utf-8 -*-

from flask import Flask, jsonify, render_template
from flask import request
from flask_cors import CORS, cross_origin

import json

import datetime
from optparse import OptionParser
from config import Config

from valkey_manager import RedisManager
from valkey_explainer import RedisExplainer
from store import get_store_manager
from poller import Poller
from async_job import AsyncJob
import multiprocessing as mp

g_server_addr = None
POLLING_INTERVAL = 1
PERIOD = 3600

parser = OptionParser()
parser.add_option("-a", "--addr", dest="addr", default="127.0.0.1", help="hostaddr")
parser.add_option("-c", "--config", dest="config", help="configfile")
(options, args) = parser.parse_args()

target_mgr = RedisManager(addr=options.addr)
queue = mp.Queue()

config = None
store_config = None
if options.config and options.config is not None:
    config = Config(options.config)
    store_config = config.get("store")


store_mgr = None


app = Flask(__name__)
cors = CORS(app)


async_job_executed = False
async_job = None


def get_current_timestamp():
    return int(datetime.datetime.utcnow().timestamp())


def parse_info(info: dict):
    return info


def get_valkey_save_info(mgr):
    return mgr.get_config("save")['save']
    
def collect_valkey_info(mgr):
    info = mgr.info()
    return parse_info(info)


def sensor():
    host = target_mgr.get_host()
    value = collect_valkey_info(target_mgr)
    value["time"] = get_current_timestamp()
    store_mgr.append(host, json.dumps(value))


poller = Poller.instance()


def make_histories(values):
    len_of_vals = len(values)
    p0 = values[0]
    c = p0['total_commands_processed']
    tc = []
    labels = []
    rss = []
    for i in range(1, len_of_vals):
        p = values[i]['total_commands_processed']
        label = datetime.datetime.fromtimestamp(values[i]['time']).strftime("%Y-%m-%d %H:%M:%S")
        rs = values[i]['used_memory_rss']/1024/1024/1024
        v = p - c
        c = p
        tc.append(v)
        labels.append(label)
        rss.append(rs)
        
    return {'commands': tc, 'labels': labels, 'rss': rss}


def check_size(queue, args):
    (limit) = args
    valkey_mgr = RedisManager(addr=options.addr)
    all = valkey_mgr.check_size(limit)
    queue.put(all)

    
def Resp(code=0, message="ok"):
    return {'code': code, 'message': message}


@app.route('/')
def index():
    global g_server_addr, POLLING_INTERVAL
    return render_template('index.html', SERVER_ADDR = g_server_addr, interval = POLLING_INTERVAL*1000)


@app.route('/api/v1/item_size_result', methods=['GET'])
def item_size_result():
    global async_job_executed
    global async_job

    if not async_job_executed:
        return Resp(-100, "No Check Size Job")

    resp = Resp()
    v = async_job.get()
    if v is not None:
        resp["data"] = v 
        async_job.join()
        async_job = None
        async_job_executed = False
        return resp
    else:
        return Resp(200, "In Progress")


@app.route('/api/v1/item_size/<limit>', methods=['GET'])
def item_size(limit=1024768):
    limit = int(limit)
    global async_job
    global async_job_executed
    resp = Resp()
    if async_job_executed:
        return Resp(-100, "Already Check Size Progress")
    else:
        async_job_executed = True
        async_job = AsyncJob(check_size, queue, args=(limit)) 
        async_job.start()

    return resp
        

def produce_graph_data(host):
    values = [json.loads(x) for x in store_mgr.get(host)]
    if values is None or len(values) == 0:
        return None

    last = values[-1]
    results = make_histories(values)
    explainer = RedisExplainer(values)
    results['explains'] = explainer.explain()
    results['memory'] = {
        'rss': last['used_memory_rss_human'],
        'used': last['used_memory_human'],
        'peak': last['used_memory_peak_human'],
        'ratio': 0
    }

    if "total_system_memory_human" in last:
        results['memory']['total'] = last["total_system_memory_human"]
        results['memory']['ratio'] = str(int(float(last["used_memory"]) / float(last["total_system_memory"]) * 100)) + "%"

    if "maxmemory" in last:
        if last["maxmemory"] > 0:
            results['memory']['ratio'] = str(int(float(last["used_memory"]) / float(last["maxmemory"]) * 100)) + "%"

    return results


@app.route('/api/v1/info', methods=['GET'])
def analysis():
    now = get_current_timestamp()

    hosts = store_mgr.keys()
    r = {}
    for host in hosts:
        result = produce_graph_data(host)
        if result:
            r[host] = result

    resp = Resp()
    resp['data'] = r
    resp['time'] = now
    return resp


@app.route('/api/v1/hello', methods=['GET'])
def hello():
    return target_mgr.addr


def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


if __name__ == '__main__':
    addr = "0.0.0.0"
    port = 5000

    if not config:
        g_server_addr = get_local_ip() + f":{port}"
    else:
        app_config = config.get("app")
        POLLING_INTERVAL = int(app_config.get("interval"))
        g_server_addr = get_local_ip() + ":" + app_config.get("port")
        addr = app_config.get("host")
        port = int(app_config.get("port"))

    store_mgr = get_store_manager(store_config, PERIOD/POLLING_INTERVAL)
    poller.add(sensor, POLLING_INTERVAL)
    app.run(host=addr, port=port)
