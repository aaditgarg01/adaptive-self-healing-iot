import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS nodes(node_id TEXT PRIMARY KEY,x REAL NOT NULL,y REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS telemetry(node_id TEXT,boot_id TEXT,sequence INTEGER,received REAL,payload TEXT,PRIMARY KEY(node_id,boot_id,sequence));
        CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,created TEXT DEFAULT CURRENT_TIMESTAMP,config TEXT,result TEXT);
        """)
        self.db.commit()

    def register(self, node, x, y):
        self.db.execute(
            "INSERT INTO nodes VALUES(?,?,?) ON CONFLICT(node_id) DO UPDATE SET x=excluded.x,y=excluded.y",
            (node, x, y),
        )
        self.db.commit()

    def nodes(self):
        return self.db.execute(
            "SELECT node_id,x,y FROM nodes ORDER BY node_id"
        ).fetchall()

    def ingest(self, payload, received):
        try:
            self.db.execute(
                "INSERT INTO telemetry VALUES(?,?,?,?,?)",
                (
                    payload["node_id"],
                    payload["boot_id"],
                    payload["sequence"],
                    received,
                    json.dumps(payload),
                ),
            )
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def save_run(self, config, result):
        self.db.execute(
            "INSERT INTO runs(config,result) VALUES(?,?)",
            (json.dumps(config), json.dumps(result)),
        )
        self.db.commit()

    def runs(self):
        return [
            {"id": i, "created": t, "config": json.loads(c), "result": json.loads(r)}
            for i, t, c, r in self.db.execute(
                "SELECT id,created,config,result FROM runs ORDER BY id DESC LIMIT 100"
            )
        ]

    def close(self):
        self.db.close()
