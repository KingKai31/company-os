import os
import concurrent.futures
from azure.cosmos import CosmosClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

COSMOS_TIMEOUT = int(os.getenv("COSMOS_TIMEOUT", "12"))

_client = None
_database = None
_container = None


def _get_container():
    global _client, _database, _container
    if _container is None:
        conn = os.getenv("COSMOS_CONNECTION_STRING")
        if not conn:
            raise ValueError("COSMOS_CONNECTION_STRING not set in .env")
        _client = CosmosClient.from_connection_string(conn)
        _database = _client.get_database_client("company_os")
        _container = _database.get_container_client("agent_state")
    return _container


def _run_with_timeout(fn, timeout=COSMOS_TIMEOUT, default=None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"[BRAIN] Cosmos DB operation timed out after {timeout}s")
            return default
        except Exception as e:
            print(f"[BRAIN] Cosmos DB error: {e}")
            return default


def write_state(agent_id, data):
    def _write():
        container = _get_container()
        item = {
            "id": agent_id,
            "agent_id": agent_id,
            "data": data,
            "updated_at": datetime.utcnow().isoformat(),
        }
        container.upsert_item(item)
        print(f"[BRAIN] {agent_id} wrote state")
        return item

    result = _run_with_timeout(_write, default=None)
    if result is None:
        print(f"[BRAIN] Write failed or timed out for {agent_id}")
    return result


def read_state(agent_id):
    def _read():
        container = _get_container()
        item = container.read_item(item=agent_id, partition_key=agent_id)
        return item.get("data", {})

    return _run_with_timeout(_read, default={})


def read_all_states():
    def _read_all():
        container = _get_container()
        items = list(container.read_all_items())
        return {item["agent_id"]: item.get("data", {}) for item in items}

    return _run_with_timeout(_read_all, default={})


def clear_all():
    def _clear():
        container = _get_container()
        items = list(container.read_all_items())
        for item in items:
            container.delete_item(item=item["id"], partition_key=item["agent_id"])
        print("[BRAIN] Cleared all states")
        return True

    return _run_with_timeout(_clear, default=False)
