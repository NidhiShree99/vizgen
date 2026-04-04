import sqlite3
import json


def get_connection():
    conn = sqlite3.connect("vizgen.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS dashboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            share_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard_id INTEGER NOT NULL,
            prompt TEXT,
            chart_type TEXT,
            chart_config TEXT,
            position INTEGER DEFAULT 0,
            width TEXT DEFAULT 'half',
            height INTEGER DEFAULT 320,
            data_json TEXT,
            FOREIGN KEY (dashboard_id) REFERENCES dashboards(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS prompt_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tile_id INTEGER,
            prompt_text TEXT,
            chart_config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tile_id) REFERENCES tiles(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard_id INTEGER NOT NULL,
            version_num INTEGER NOT NULL,
            tiles_snapshot TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dashboard_id) REFERENCES dashboards(id)
        )
    """)

    conn.commit()
    conn.close()


def save_dashboard(name, status="draft", share_token=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO dashboards (name, status, share_token) "
        "VALUES (?, ?, ?)",
        (name, status, share_token)
    )
    conn.commit()
    dashboard_id = c.lastrowid
    conn.close()
    return dashboard_id


def update_dashboard_name(dashboard_id, name):
    conn = get_connection()
    conn.execute(
        "UPDATE dashboards SET name = ? WHERE id = ?",
        (name, dashboard_id)
    )
    conn.commit()
    conn.close()


def update_dashboard_publish(dashboard_id, share_token):
    conn = get_connection()
    conn.execute(
        "UPDATE dashboards SET status = 'published', "
        "share_token = ? WHERE id = ?",
        (share_token, dashboard_id)
    )
    conn.commit()
    conn.close()


def get_user_dashboards():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM dashboards ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dashboard_by_token(token):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM dashboards WHERE share_token = ?",
        (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_dashboard_by_id(dashboard_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM dashboards WHERE id = ?",
        (dashboard_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_dashboard(dashboard_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM tiles WHERE dashboard_id = ?",
        (dashboard_id,)
    )
    conn.execute(
        "DELETE FROM dashboard_versions WHERE dashboard_id = ?",
        (dashboard_id,)
    )
    conn.execute(
        "DELETE FROM dashboards WHERE id = ?",
        (dashboard_id,)
    )
    conn.commit()
    conn.close()


def delete_dashboard_tiles(dashboard_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM tiles WHERE dashboard_id = ?",
        (dashboard_id,)
    )
    conn.commit()
    conn.close()


def save_tile(dashboard_id, prompt, config, position,
              width="half", height=320, data_json=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO tiles
           (dashboard_id, prompt, chart_type, chart_config,
            position, width, height, data_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (dashboard_id, prompt, config["chart_type"],
         json.dumps(config), position, width, height, data_json)
    )
    conn.commit()
    tile_id = c.lastrowid
    conn.close()
    return tile_id


def get_dashboard_tiles(dashboard_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tiles WHERE dashboard_id = ? "
        "ORDER BY position",
        (dashboard_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_prompt_history(tile_id, prompt_text, chart_config):
    conn = get_connection()
    conn.execute(
        "INSERT INTO prompt_history "
        "(tile_id, prompt_text, chart_config) VALUES (?, ?, ?)",
        (tile_id, prompt_text, json.dumps(chart_config))
    )
    conn.commit()
    conn.close()


def save_version(dashboard_id, tiles_snapshot):
    conn = get_connection()
    c = conn.cursor()

    row = conn.execute(
        "SELECT MAX(version_num) as max_v "
        "FROM dashboard_versions "
        "WHERE dashboard_id = ?",
        (dashboard_id,)
    ).fetchone()
    next_version = (row["max_v"] or 0) + 1

    c.execute(
        "INSERT INTO dashboard_versions "
        "(dashboard_id, version_num, tiles_snapshot) "
        "VALUES (?, ?, ?)",
        (dashboard_id, next_version, tiles_snapshot)
    )
    conn.commit()

    # Keep last 3 versions — current + 2 backups
    old_versions = conn.execute(
        "SELECT id FROM dashboard_versions "
        "WHERE dashboard_id = ? "
        "ORDER BY version_num DESC",
        (dashboard_id,)
    ).fetchall()

    if len(old_versions) > 3:
        ids_to_delete = [r["id"] for r in old_versions[3:]]
        for vid in ids_to_delete:
            conn.execute(
                "DELETE FROM dashboard_versions WHERE id = ?",
                (vid,)
            )
    conn.commit()
    conn.close()
    return next_version


def get_versions(dashboard_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM dashboard_versions "
        "WHERE dashboard_id = ? "
        "ORDER BY version_num DESC",
        (dashboard_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]