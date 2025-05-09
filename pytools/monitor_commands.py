import collections
import redis
import sys


class Monitor():
    def __init__(self, connection_pool):
        self.key_counter = collections.Counter()
        self.connection_pool = connection_pool
        self.connection = None
        self.run = True

    def __del__(self):
        try:
            self.reset()
        except Exception:
            pass

    def reset(self):
        if self.connection:
            self.connection_pool.release(self.connection)
            self.connection = None

    def monitor(self):
        if self.connection is None:
            self.connection = self.connection_pool.get_connection(
                'monitor', None)
        self.connection.send_command("monitor")
        return self.listen()

    def parse_response(self):
        return self.connection.read_response()

    def listen(self):
        while self.run:
            try:
                yield self.parse(self.parse_response())
            except Exception:
                self.run = False

    def parse(self, response):
        value = response.decode('utf-8')
        parts = value.split()
        if len(parts) > 4:
            # db = parts[1][1:]
            # host = parts[2][:-1]
            # cmd = parts[3]
            key = parts[4]

            self.key_counter[key] += 1

        return response
        

if  __name__ == '__main__':
    host = sys.argv[1]
    port = int(sys.argv[2])
    N = 100
    try:
        N = int(sys.argv[3])
    except Exception:
        N = 100

    pool = redis.ConnectionPool(host=host, port=port, db=0)
    monitor = Monitor(pool)
    commands = monitor.monitor()

    for c in commands :
        if not monitor.run:
            print("")
            break

    print("Valkey Key Monitor Most Common 100")
    for k, v in monitor.key_counter.most_common(N):
        print(k, v)
