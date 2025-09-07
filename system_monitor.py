
import argparse
import logging
from logging.handlers import RotatingFileHandler
import time
from datetime import datetime, timezone
import os
import psutil
import sqlite3
from typing import Optional, Tuple

def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S%z')

def init_logger(log_file: str, max_bytes: int, backups: int) -> logging.Logger:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger = logging.getLogger('system_health')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backups, encoding='utf-8')
    fmt = logging.Formatter('[%(asctime)s] %(levelname)-7s %(message)s')
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    # Also log to console
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)
    return logger

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            ts TEXT,
            cpu_pct REAL,
            mem_pct REAL,
            disk_pct REAL,
            net_sent INTEGER,
            net_recv INTEGER
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS events (
            ts TEXT,
            level TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    return conn

def get_snapshot(prev_net: Optional[Tuple[int, int]]):
    cpu_pct = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    mem_pct = mem.percent
    disk = psutil.disk_usage('/')
    disk_pct = disk.percent

    net = psutil.net_io_counters()
    net_sent = net.bytes_sent
    net_recv = net.bytes_recv

    delta_sent = 0
    delta_recv = 0
    if prev_net is not None:
        delta_sent = max(0, net_sent - prev_net[0])
        delta_recv = max(0, net_recv - prev_net[1])

    return cpu_pct, mem_pct, disk_pct, net_sent, net_recv, delta_sent, delta_recv

def human_bytes(n: int) -> str:
    # Simple bytes formatter
    step = 1024.0
    units = ['B','KB','MB','GB','TB']
    i = 0
    f = float(n)
    while f >= step and i < len(units)-1:
        f /= step
        i += 1
    if f >= 10 or f.is_integer():
        return f"{int(f)} {units[i]}"
    return f"{f:.1f} {units[i]}"

def main():
    parser = argparse.ArgumentParser(description='System Health Monitor')
    parser.add_argument('--interval', type=int, default=5, help='Seconds between samples (default: 5)')
    parser.add_argument('--duration', type=int, default=None, help='Total seconds to run (default: run indefinitely)')
    parser.add_argument('--cpu-th', type=int, default=80, help='CPU usage %% threshold for warning (default: 80)')
    parser.add_argument('--mem-th', type=int, default=80, help='Memory usage %% threshold for warning (default: 80)')
    parser.add_argument('--disk-th', type=int, default=90, help='Disk usage %% threshold for warning (default: 90)')
    parser.add_argument('--log-file', type=str, default=os.path.join('logs', 'system_health.log'), help='Path to log file')
    parser.add_argument('--log-max-bytes', type=int, default=1_000_000, help='Max bytes per log file before rotation')
    parser.add_argument('--log-backups', type=int, default=5, help='Number of rotated log backups to keep')
    parser.add_argument('--db', type=str, default=None, help='Path to SQLite database file (optional)')
    args = parser.parse_args()

    logger = init_logger(args.log_file, args.log_max_bytes, args.log_backups)
    conn = None
    if args.db:
        conn = init_db(args.db)

    start_time = time.time()
    prev_net = None  # (bytes_sent, bytes_recv)

    # Prime CPU measurement for more accurate first read
    psutil.cpu_percent(interval=None)

    while True:
        now = iso_now()
        cpu_pct, mem_pct, disk_pct, net_sent, net_recv, d_sent, d_recv = get_snapshot(prev_net)

        msg = (f'CPU: {cpu_pct:.1f}%, MEM: {mem_pct:.1f}%, DISK: {disk_pct:.1f}%, '
               f'NET Δ Sent: {human_bytes(d_sent)}, Δ Recv: {human_bytes(d_recv)}')
        level = 'INFO'

        if cpu_pct >= args.cpu_th:
            level = 'WARNING'
            logger.warning(f'High CPU Usage: {cpu_pct:.1f}%')
        if mem_pct >= args.mem_th:
            level = 'WARNING'
            logger.warning(f'High Memory Usage: {mem_pct:.1f}%')
        if disk_pct >= args.disk_th:
            level = 'ERROR'
            logger.error(f'Disk Usage Critical: {disk_pct:.1f}%')

        # Always log the summary line at INFO
        logger.info(msg)

        # Persist to DB if requested
        if conn:
            cur = conn.cursor()
            cur.execute('INSERT INTO metrics (ts, cpu_pct, mem_pct, disk_pct, net_sent, net_recv) VALUES (?, ?, ?, ?, ?, ?)',
                        (now, cpu_pct, mem_pct, disk_pct, net_sent, net_recv))
            # Insert events corresponding to thresholds
            if cpu_pct >= args.cpu_th:
                cur.execute('INSERT INTO events (ts, level, message) VALUES (?, ?, ?)',
                            (now, 'WARNING', f'High CPU Usage: {cpu_pct:.1f}%'))
            if mem_pct >= args.mem_th:
                cur.execute('INSERT INTO events (ts, level, message) VALUES (?, ?, ?)',
                            (now, 'WARNING', f'High Memory Usage: {mem_pct:.1f}%'))
            if disk_pct >= args.disk_th:
                cur.execute('INSERT INTO events (ts, level, message) VALUES (?, ?, ?)',
                            (now, 'ERROR', f'Disk Usage Critical: {disk_pct:.1f}%'))
            conn.commit()

        prev_net = (net_sent, net_recv)

        # Exit if duration reached
        if args.duration is not None and (time.time() - start_time) >= args.duration:
            break

        time.sleep(max(1, args.interval))

    if conn:
        conn.close()

if __name__ == '__main__':
    main()
