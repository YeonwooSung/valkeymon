import redis
import sys


VALKEY_HOST = sys.argv[1]
VALKEY_PORT = sys.argv[2]

underbound = 1024768

if len(sys.argv) >= 4:
    underbound = int(sys.argv[3])

def get_string_key_size(conn, key):
    return len(conn.get("key"))

def get_hash_key_size(conn, key):
    return len(conn.hgetall(key))

def get_set_key_size(conn, key):
    return len(conn.smembers(key))

def dump(conn, key):
    data = conn.dump(key)
    return len(data) if data else 0


rconn = redis.StrictRedis(VALKEY_HOST, VALKEY_PORT)

store = {}
for key in rconn.scan_iter(count=100):
    dtype = rconn.type(key)
    size = dump(rconn, key)
    if size >= underbound:
        if size not in store:
            store[size] = []

        store[size].append((dtype, key))

for elem in sorted(store.items(), reverse=True) :
    print(elem[0])
    for item in elem[1]:
        print(" ====> ", item)
