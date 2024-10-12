# valkeymon
Valkey Monitoring Tool (also works with Redis)

## How to use redismon

* Run Valkeymon

```
python app.py -a {VALKEY_HOST}:{VALKEY_PORT}
```

or

* Create Config file
```
[app]
port = 5000
host = 0.0.0.0
elasticache = no

[redis]
host = 192.168.0.102
port = 6379
```

and Run Valkeymon
```
python app.py -c ./valkeymon.ini
```

### screenshot

![redismon](https://user-images.githubusercontent.com/439301/155867717-76d7f1a0-fadb-4e6b-8aad-75e551db46c5.png)

## References

This project uses [charsyam/redis](https://github.com/charsyam/redismon) as a starting point.
Credits to [charsyam](https://github.com/charsyam) for the original work.
