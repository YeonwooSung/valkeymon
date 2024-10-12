from database import init_db
from mysql_store import MysqlStore
from memory_store import MemoryStore


def get_store_manager(store_config=None, limit=120):
    if store_config and store_config.get("mode") == "mysql_store":
        _db_session = init_db(store_config.get("uri"))
        return MysqlStore(_db_session, limit)
    else:
        return MemoryStore(limit)
