import json
import os
import io
import sqlite3
import datetime

DB_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db_config.json')


def load_config():
    try:
        with open(DB_CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {"db_type": "sqlite"}


def save_config(cfg):
    with open(DB_CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)


def get_db_uri():
    # Prefer DATABASE_URL from environment (e.g. Replit PostgreSQL)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # SQLAlchemy requires postgresql:// not postgres://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url

    cfg = load_config()
    if cfg.get('db_type') == 'mysql':
        h = cfg.get('mysql_host', 'localhost')
        p = cfg.get('mysql_port', 3306)
        d = cfg.get('mysql_database', '')
        u = cfg.get('mysql_user', '')
        pw = cfg.get('mysql_password', '')
        # Verify connection is reachable before committing to MySQL
        ok, _ = test_mysql_connection(h, p, d, u, pw)
        if ok:
            return f'mysql+pymysql://{u}:{pw}@{h}:{p}/{d}'
        import logging
        logging.warning(
            'MySQL database configured but unreachable (%s:%s). '
            'Falling back to SQLite. Fix the connection in the admin Database panel.',
            h, p
        )
    db_path = os.path.join(os.path.dirname(DB_CONFIG_PATH), 'resume_app.db')
    return f'sqlite:///{db_path}'


def test_mysql_connection(host, port, database, user, password, use_ssl=False):
    try:
        import pymysql
        kwargs = dict(
            host=host,
            port=int(port),
            database=database,
            user=user,
            password=password,
            connect_timeout=8,
        )
        if use_ssl:
            kwargs['ssl'] = {'ca': None}
        conn = pymysql.connect(**kwargs)
        version = conn.get_server_info()
        conn.close()
        return True, f'Connected — MySQL server version {version}'
    except pymysql.err.OperationalError as e:
        code = e.args[0] if e.args else 0
        msg = e.args[1] if len(e.args) > 1 else str(e)
        if code == 2003 or 'timed out' in str(msg).lower() or 'connection refused' in str(msg).lower():
            hint = (
                f'Cannot reach {host}:{port}. Common causes:\n'
                '• The host blocks external IPs (e.g. PythonAnywhere only allows connections from their own network)\n'
                '• Port 3306 is firewalled — ask your host to allowlist this server\'s IP\n'
                '• Wrong host/port — double-check your database provider\'s connection details\n'
                '• Try enabling SSL if your host requires it'
            )
            return False, hint
        if code == 1045:
            return False, f'Access denied for user "{user}" — check your username and password'
        if code == 1049:
            return False, f'Unknown database "{database}" — make sure the database exists on the server'
        return False, f'MySQL error ({code}): {msg}'
    except Exception as e:
        return False, str(e)


def _escape_sql_value(val):
    if val is None:
        return 'NULL'
    if isinstance(val, bool):
        return '1' if val else '0'
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return f"'{val.isoformat()}'"
    s = str(val).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def export_as_sqlite():
    """Return a bytes object containing a SQLite .db dump (SQL text)."""
    cfg = load_config()
    db_type = cfg.get('db_type', 'sqlite')

    if db_type == 'sqlite':
        db_path = os.path.join(os.path.dirname(DB_CONFIG_PATH), 'resume_app.db')
        conn = sqlite3.connect(db_path)
        lines = list(conn.iterdump())
        conn.close()
        return '\n'.join(lines).encode('utf-8')

    # MySQL source → generate SQLite-compatible SQL
    return _export_mysql_to_sqlite_sql(cfg)


def _export_mysql_to_sqlite_sql(cfg):
    import pymysql
    conn = pymysql.connect(
        host=cfg.get('mysql_host', 'localhost'),
        port=int(cfg.get('mysql_port', 3306)),
        database=cfg.get('mysql_database', ''),
        user=cfg.get('mysql_user', ''),
        password=cfg.get('mysql_password', ''),
    )
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [row[0] for row in cur.fetchall()]

    buf = io.StringIO()
    buf.write("BEGIN TRANSACTION;\n")
    for table in tables:
        cur.execute(f"DESCRIBE `{table}`")
        cols = cur.fetchall()
        col_defs = []
        for col in cols:
            name, typ, null, key, default, extra = col
            sqlite_type = 'TEXT'
            t = typ.upper()
            if any(x in t for x in ('INT',)):
                sqlite_type = 'INTEGER'
            elif any(x in t for x in ('FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC')):
                sqlite_type = 'REAL'
            pk = ' PRIMARY KEY' if key == 'PRI' else ''
            nn = ' NOT NULL' if null == 'NO' and key != 'PRI' else ''
            col_defs.append(f'  "{name}" {sqlite_type}{pk}{nn}')
        buf.write(f'CREATE TABLE IF NOT EXISTS "{table}" (\n')
        buf.write(',\n'.join(col_defs))
        buf.write('\n);\n')

        col_names = [c[0] for c in cols]
        cur.execute(f"SELECT * FROM `{table}`")
        rows = cur.fetchall()
        for row in rows:
            vals = ', '.join(_escape_sql_value(v) for v in row)
            cols_str = ', '.join(f'"{c}"' for c in col_names)
            buf.write(f'INSERT INTO "{table}" ({cols_str}) VALUES ({vals});\n')
    buf.write("COMMIT;\n")
    conn.close()
    return buf.getvalue().encode('utf-8')


def export_as_mysql():
    """Return bytes of a MySQL-compatible SQL dump."""
    cfg = load_config()
    db_type = cfg.get('db_type', 'sqlite')

    if db_type == 'mysql':
        return _export_mysql_dump(cfg)
    return _export_sqlite_to_mysql_sql()


def import_sql_dump(sql_text, cfg=None):
    """Import a SQL dump into the current active database. Returns result dict."""
    if cfg is None:
        cfg = load_config()

    db_type = cfg.get('db_type', 'sqlite')
    # If MySQL is configured but we're actually using SQLite (fallback), import to SQLite
    if db_type == 'mysql':
        ok, _ = test_mysql_connection(
            cfg.get('mysql_host'), cfg.get('mysql_port', 3306),
            cfg.get('mysql_database'), cfg.get('mysql_user'), cfg.get('mysql_password')
        )
        if not ok:
            db_type = 'sqlite'

    if db_type == 'mysql':
        return _import_sql_to_mysql(sql_text, cfg)
    return _import_sql_to_sqlite(sql_text)


def _import_sql_to_sqlite(sql_text):
    db_path = os.path.join(os.path.dirname(DB_CONFIG_PATH), 'resume_app.db')
    conn = sqlite3.connect(db_path)
    executed = 0
    errors = []
    try:
        # Split by semicolons, skip blank/comment lines
        statements = [s.strip() for s in sql_text.split(';') if s.strip()]
        for stmt in statements:
            lines = [l for l in stmt.splitlines() if not l.strip().startswith('--')]
            clean = '\n'.join(lines).strip()
            if not clean:
                continue
            try:
                conn.execute(clean)
                executed += 1
            except Exception as e:
                errors.append(str(e)[:120])
        conn.commit()
    finally:
        conn.close()
    return {
        'success': True,
        'message': f'Imported into SQLite: {executed} statements executed.',
        'errors': errors[:10],
    }


def _import_sql_to_mysql(sql_text, cfg):
    import pymysql
    conn = pymysql.connect(
        host=cfg.get('mysql_host'), port=int(cfg.get('mysql_port', 3306)),
        database=cfg.get('mysql_database'), user=cfg.get('mysql_user'),
        password=cfg.get('mysql_password'), autocommit=False,
    )
    cur = conn.cursor()
    executed = 0
    errors = []
    statements = [s.strip() for s in sql_text.split(';') if s.strip()]
    for stmt in statements:
        lines = [l for l in stmt.splitlines() if not l.strip().startswith('--')]
        clean = '\n'.join(lines).strip()
        if not clean:
            continue
        try:
            cur.execute(clean)
            executed += 1
        except Exception as e:
            errors.append(str(e)[:120])
    conn.commit()
    conn.close()
    return {
        'success': True,
        'message': f'Imported into MySQL: {executed} statements executed.',
        'errors': errors[:10],
    }


def _export_sqlite_to_mysql_sql():
    db_path = os.path.join(os.path.dirname(DB_CONFIG_PATH), 'resume_app.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cur.fetchall()]

    buf = io.StringIO()
    buf.write("-- MySQL dump generated by AI Resume App\n")
    buf.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n\n")

    for table in tables:
        cur.execute(f"PRAGMA table_info(`{table}`)")
        cols_info = cur.fetchall()

        buf.write(f"DROP TABLE IF EXISTS `{table}`;\n")
        buf.write(f"CREATE TABLE `{table}` (\n")
        col_defs = []
        pk_col = None
        for col in cols_info:
            cid, name, typ, notnull, dflt, pk = col
            mysql_type = 'LONGTEXT'
            t = typ.upper()
            if 'INT' in t:
                mysql_type = 'INT'
            elif any(x in t for x in ('REAL', 'FLOAT', 'DOUBLE', 'NUMERIC')):
                mysql_type = 'DOUBLE'
            if pk:
                pk_col = name
            ai = ' AUTO_INCREMENT' if pk else ''
            nn = ' NOT NULL' if notnull else ''
            col_defs.append(f'  `{name}` {mysql_type}{nn}{ai}')
        if pk_col:
            col_defs.append(f'  PRIMARY KEY (`{pk_col}`)')
        buf.write(',\n'.join(col_defs))
        buf.write('\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n\n')

        col_names = [c[1] for c in cols_info]
        cur.execute(f"SELECT * FROM `{table}`")
        rows = cur.fetchall()
        if rows:
            buf.write(f"INSERT INTO `{table}` (`{'`, `'.join(col_names)}`) VALUES\n")
            row_strs = []
            for row in rows:
                vals = ', '.join(_escape_sql_value(v) for v in row)
                row_strs.append(f'  ({vals})')
            buf.write(',\n'.join(row_strs))
            buf.write(';\n\n')

    buf.write("SET FOREIGN_KEY_CHECKS=1;\n")
    conn.close()
    return buf.getvalue().encode('utf-8')


def _export_mysql_dump(cfg):
    import pymysql
    conn = pymysql.connect(
        host=cfg.get('mysql_host', 'localhost'),
        port=int(cfg.get('mysql_port', 3306)),
        database=cfg.get('mysql_database', ''),
        user=cfg.get('mysql_user', ''),
        password=cfg.get('mysql_password', ''),
    )
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [row[0] for row in cur.fetchall()]

    buf = io.StringIO()
    buf.write("-- MySQL dump generated by AI Resume App\n")
    buf.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n\n")

    for table in tables:
        cur.execute(f"SHOW CREATE TABLE `{table}`")
        create_stmt = cur.fetchone()[1]
        buf.write(f"DROP TABLE IF EXISTS `{table}`;\n")
        buf.write(create_stmt + ";\n\n")

        cur.execute(f"DESCRIBE `{table}`")
        cols = [c[0] for c in cur.fetchall()]
        cur.execute(f"SELECT * FROM `{table}`")
        rows = cur.fetchall()
        if rows:
            buf.write(f"INSERT INTO `{table}` (`{'`, `'.join(cols)}`) VALUES\n")
            row_strs = []
            for row in rows:
                vals = ', '.join(_escape_sql_value(v) for v in row)
                row_strs.append(f'  ({vals})')
            buf.write(',\n'.join(row_strs))
            buf.write(';\n\n')

    buf.write("SET FOREIGN_KEY_CHECKS=1;\n")
    conn.close()
    return buf.getvalue().encode('utf-8')
