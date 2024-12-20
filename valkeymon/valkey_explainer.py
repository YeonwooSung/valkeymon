# import json


PTIME = "ptime"
CALLS = "calls"
CMDSTAT_KEYS = "cmdstat_keys"
INFO = 0
STAT = 1


def base_check(name, calls, ptime, call_limit, ptime_limit, check_type, description):
    if ptime >= ptime_limit and calls > call_limit:
        return {'name': name, 'type': 'cmd', 'value': ptime, 'data_type': check_type, 'description': description}


def base_stat_check(name, value, value_limit, description):
    if value >= value_limit:
        return {'name': name, 'type': 'stat', 'value': value, 'data_type': 'value', 'description': description}
        

def explain_slow_cmd(cmd, calls, ptime, call_limit, ptime_limit):
    return base_check(cmd, calls, ptime, call_limit, ptime_limit, PTIME, "some keys have large value")


def explain_ON_cmd(cmd, calls, ptime, call_limit, ptime_limit):
    return base_check(cmd, calls, ptime, call_limit, ptime_limit, PTIME, "You may get all data from large collections")


def explain_keys_cmd(cmd, calls, ptime, call_limit, ptime_limit):
    return base_check(cmd, calls, ptime, call_limit, ptime_limit, PTIME, "Don't use keys command")


def explain_client_cmd(cmd, calls, ptime, call_limit, ptime_limit):
    return base_check(cmd, calls, ptime, call_limit, ptime_limit, PTIME, "You have too many connections")


def explain_cluster_cmd(cmd, calls, ptime, call_limit, ptime_limit):
    return base_check(cmd, calls, ptime, call_limit, ptime_limit, PTIME, "cluster command is basically slow command")


def explain_clients_stat(stat, value, value_limit):
    return base_stat_check(stat, value, value_limit, "connected_clients value is changed a lot")


def explain_valkey_version(stat, value, value_limit):
    if value[0] < '6':
        description = "Recommand Redis 6.x for failover, Redis 6.x support PSYNC2 better"
        return {'name': stat, 'type': 'info', 'value': value, 'data_type': 'value', 'description': description}


EXPLAIN_STATS_MAP = {
    "connected_clients":    (explain_clients_stat, STAT, 100),
    "valkey_version":     (explain_valkey_version, INFO, 0)
}

EXPLAIN_CMDS_MAP = {
    "cmdstat_get":      (explain_slow_cmd, 1, 20.0),
    "cmdstat_del":      (explain_slow_cmd, 1, 20.0),
    "cmdstat_hget":      (explain_slow_cmd, 1, 10.0),
    CMDSTAT_KEYS:      (explain_keys_cmd, 1, 0),
    "cmdstat_hmget":      (explain_slow_cmd, 1, 10.0),
    "cmdstat_client":   (explain_client_cmd, 1, 100.0),
    "cmdstat_hgetall":  (explain_ON_cmd, 1, 50.0),
    "cmdstat_hvals":  (explain_ON_cmd, 1, 50.0),
    "cmdstat_smembers":  (explain_ON_cmd, 1, 50.0),
    "cmdstat_zrange":  (explain_ON_cmd, 1, 50.0),
    "cmdstat_zrangebyscore":  (explain_ON_cmd, 1, 50.0),
    "cmdstat_zrevrange":  (explain_ON_cmd, 1, 50.0),
    "cmdstat_zrevrangebyscore":  (explain_ON_cmd, 1, 50.0),
    "cmdstat_cluster":  (explain_cluster_cmd, 1, 50.0),
}


class RedisExplainer:
    def __init__(self, values):
        self.values = values

    def explain(self):
        cmds = self.analyze_commands(self.values)
        stats = self.analyze_stats(self.values)
        results = self.explain_commands(cmds)
        stats_value = self.explain_stats(stats)
        results.extend(stats_value)
        return results

    def explain_stats(self, stats):
        results = []
        for k, v in stats.items():
            value = v

            if k in EXPLAIN_STATS_MAP:
                m = EXPLAIN_STATS_MAP[k]
                call = m[0]
                t = m[1]
                value_limit = m[2]

                ret = call(k, v, value_limit)
                if ret is not None:
                    results.append(ret)

        return results

    def explain_commands(self, cmds):
        results = []
        for k, v in cmds.items():
            calls = v[0]
            ptime = v[1]

            call = explain_slow_cmd
            call_limit = 0
            ptime_limit = 100

            if k in EXPLAIN_CMDS_MAP:
                m = EXPLAIN_CMDS_MAP[k]
                call = m[0]
                call_limit = m[1]
                ptime_limit = m[2]

            ret = call(k, calls, ptime, call_limit, ptime_limit)
            if ret is not None:
                results.append(ret)

        return results

    def get_commands(self, info):
        cmds = []

        for key in info.keys():
            if key.startswith("cmdstat_"):
                cmds.append((key, info[key]))

        return cmds

    def get_stats(self, info):
        stats = []

        for key in info.keys():
            if key in EXPLAIN_STATS_MAP:
                stats.append((key, info[key]))

        return stats

    def analyze_stats(self, values):
        stats = []
        for value in values:
            stats.append(self.get_stats(value))

        results = {}
        for i in range(len(stats) - 1):
            current_stats = stats[i]
            next_stats = stats[i+1]

            statMap = {k:v for k, v in current_stats}
            for stat in next_stats:
                k = stat[0]
                v = stat[1]

                if k not in EXPLAIN_STATS_MAP:
                    continue

                m = EXPLAIN_STATS_MAP[k]

                if m[1] == STAT:
                    v1 = statMap[k]
                    results[k] = abs(v - v1)
                elif m[1] == INFO:
                    results[k] = v

        return results

    def analyze_commands(self, values):
        cmds = []
        for value in values:
            cmds.append(self.get_commands(value))

        results = {}
        first_appeared_map = {}
        for i in range(len(cmds) - 1):
            current_cmds = cmds[i]
            next_cmds = cmds[i+1]

            cmdMap = {k:v for k, v in current_cmds}
            for cmd in next_cmds:
                k = cmd[0]
                v = cmd[1]

                if k not in EXPLAIN_CMDS_MAP:
                    continue

                if k in cmdMap:
                    v1 = cmdMap[k]
                    if EXPLAIN_CMDS_MAP[k][1] > 0:
                        if k not in first_appeared_map:
                            first_appeared_map[k] = v["calls"]
                            
                        old = first_appeared_map[k] 
                        calls = v["calls"] - old
                    else:
                        calls = v["calls"] - v1["calls"]
                    results[k] = (calls, v["usec_per_call"])
                else:
                    results[k] = (v["calls"], v["usec_per_call"])

        return results
