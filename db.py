import os
import json
import psycopg2
import psycopg2.extras
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(
        DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor
    )
    return conn


def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS dashboards (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            share_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tiles (
            id SERIAL PRIMARY KEY,
            dashboard_id INTEGER NOT NULL REFERENCES dashboards(id),
            prompt TEXT,
            chart_type TEXT,
            chart_config TEXT,
            position INTEGER DEFAULT 0,
            width TEXT DEFAULT 'half',
            height INTEGER DEFAULT 320,
            data_json TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS prompt_history (
            id SERIAL PRIMARY KEY,
            tile_id INTEGER REFERENCES tiles(id),
            prompt_text TEXT,
            chart_config TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_versions (
            id SERIAL PRIMARY KEY,
            dashboard_id INTEGER NOT NULL REFERENCES dashboards(id),
            version_num INTEGER NOT NULL,
            tiles_snapshot TEXT,
            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_dashboard(name, status="draft", share_token=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO dashboards (name, status, share_token) "
        "VALUES (%s, %s, %s) RETURNING id",
        (name, status, share_token)
    )
    dashboard_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return dashboard_id


def update_dashboard_name(dashboard_id, name):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE dashboards SET name = %s WHERE id = %s",
        (name, dashboard_id)
    )
    conn.commit()
    conn.close()


def update_dashboard_publish(dashboard_id, share_token):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE dashboards SET status = 'published', "
        "share_token = %s WHERE id = %s",
        (share_token, dashboard_id)
    )
    conn.commit()
    conn.close()


def get_user_dashboards():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM dashboards ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dashboard_by_token(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM dashboards WHERE share_token = %s",
        (token,)
    )
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_dashboard_by_id(dashboard_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM dashboards WHERE id = %s",
        (dashboard_id,)
    )
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_dashboard(dashboard_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "DELETE FROM prompt_history WHERE tile_id IN "
        "(SELECT id FROM tiles WHERE dashboard_id = %s)",
        (dashboard_id,)
    )
    c.execute(
        "DELETE FROM tiles WHERE dashboard_id = %s",
        (dashboard_id,)
    )
    c.execute(
        "DELETE FROM dashboard_versions WHERE dashboard_id = %s",
        (dashboard_id,)
    )
    c.execute(
        "DELETE FROM dashboards WHERE id = %s",
        (dashboard_id,)
    )
    conn.commit()
    conn.close()


def delete_dashboard_tiles(dashboard_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "DELETE FROM prompt_history WHERE tile_id IN "
        "(SELECT id FROM tiles WHERE dashboard_id = %s)",
        (dashboard_id,)
    )
    c.execute(
        "DELETE FROM tiles WHERE dashboard_id = %s",
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
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (dashboard_id, prompt, config["chart_type"],
         json.dumps(config), position, width, height, data_json)
    )
    tile_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return tile_id


def get_dashboard_tiles(dashboard_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM tiles WHERE dashboard_id = %s "
        "ORDER BY position",
        (dashboard_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_prompt_history(tile_id, prompt_text, chart_config):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO prompt_history "
        "(tile_id, prompt_text, chart_config) VALUES (%s, %s, %s)",
        (tile_id, prompt_text, json.dumps(chart_config))
    )
    conn.commit()
    conn.close()


def save_version(dashboard_id, tiles_snapshot):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "SELECT MAX(version_num) as max_v "
        "FROM dashboard_versions "
        "WHERE dashboard_id = %s",
        (dashboard_id,)
    )
    row = c.fetchone()
    next_version = (row["max_v"] or 0) + 1

    c.execute(
        "INSERT INTO dashboard_versions "
        "(dashboard_id, version_num, tiles_snapshot) "
        "VALUES (%s, %s, %s)",
        (dashboard_id, next_version, tiles_snapshot)
    )
    conn.commit()

    # Keep last 3 versions — current + 2 backups
    c.execute(
        "SELECT id FROM dashboard_versions "
        "WHERE dashboard_id = %s "
        "ORDER BY version_num DESC",
        (dashboard_id,)
    )
    old_versions = c.fetchall()

    if len(old_versions) > 3:
        ids_to_delete = [r["id"] for r in old_versions[3:]]
        c.execute(
            "DELETE FROM dashboard_versions WHERE id = ANY(%s)",
            (ids_to_delete,)
        )
    conn.commit()
    conn.close()
    return next_version


def get_versions(dashboard_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM dashboard_versions "
        "WHERE dashboard_id = %s "
        "ORDER BY version_num DESC",
        (dashboard_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
