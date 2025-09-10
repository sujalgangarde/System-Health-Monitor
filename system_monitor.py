import argparse
import logging
from logging.handlers import RotatingFileHandler
import time
from datetime import datetime, timezone
import os
import psutil
import sqlite3

def iso_now():
    return datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S%z')

def init_logger(path, max_bytes, backups):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logger = logging.getLogger("system_health")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("[%(asctime)s] %(levelname)-7s %(message)s")
    handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8")
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    return logger

def init_db(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS metrics (
        ts TEXT, cpu_pct REAL, mem_pct REAL, disk_pct REAL, net_sent INTEGER, net_recv INTEGER)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS events (
        ts TEXT, level TEXT, message TEXT)""")
    conn.commit()
    return conn

def get_snapshot(prev_net):
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    net = psutil.net_io_counters()
    sent, recv = net.bytes_sent, net.bytes_recv

    d_sent = max(0, sent - prev_net[0]) if prev_net else 0
    d_recv = max(0, recv - prev_net[1]) if prev_net else 0

    return cpu, mem, disk, sent, recv, d_sent, d_recv

def fmt_bytes(n):
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024: return f"{n:.1f} {unit}" if n < 10 else f"{int(n)} {unit}"
        n /= 1024
    return f"{int(n)} TB"

def main():
    p = argparse.ArgumentParser(description="System Health Monitor")
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--duration", type=int)
    p.add_argument("--cpu-th", type=int, default=80)
    p.add_argument("--mem-th", type=int, default=80)
    p.add_argument("--disk-th", type=int, default=90)
    p.add_argument("--log-file", default=os.path.join("logs","system_health.log"))
    p.add_argument("--log-max-bytes", type=int, default=1_000_000)
    p.add_argument("--log-backups", type=int, default=5)
    p.add_argument("--db", help="SQLite DB path")
    args = p.parse_args()

    logger = init_logger(args.log_file, args.log_max_bytes, args.log_backups)
    conn = init_db(args.db) if args.db else None
    cur = conn.cursor() if conn else None

    start = time.time()
    prev_net = None

    while True:
        now = iso_now()
        cpu, mem, disk, sent, recv, d_sent, d_recv = get_snapshot(prev_net)

        msg = f"CPU: {cpu:.1f}%, MEM: {mem:.1f}%, DISK: {disk:.1f}%, NET Δ Sent: {fmt_bytes(d_sent)}, Δ Recv: {fmt_bytes(d_recv)}"
        logger.info(msg)

        if cpu >= args.cpu_th: logger.warning(f"High CPU Usage: {cpu:.1f}%")
        if mem >= args.mem_th: logger.warning(f"High Memory Usage: {mem:.1f}%")
        if disk >= args.disk_th: logger.error(f"Disk Usage Critical: {disk:.1f}%")

        if conn:
            cur.execute("INSERT INTO metrics VALUES (?,?,?,?,?,?)", (now, cpu, mem, disk, sent, recv))
            if cpu >= args.cpu_th: cur.execute("INSERT INTO events VALUES (?,?,?)", (now,"WARNING",f"High CPU Usage: {cpu:.1f}%"))
            if mem >= args.mem_th: cur.execute("INSERT INTO events VALUES (?,?,?)", (now,"WARNING",f"High Memory Usage: {mem:.1f}%"))
            if disk >= args.disk_th: cur.execute("INSERT INTO events VALUES (?,?,?)", (now,"ERROR",f"Disk Usage Critical: {disk:.1f}%"))
            conn.commit()

        prev_net = (sent, recv)
        if args.duration and (time.time()-start) >= args.duration: break
        time.sleep(max(1, args.interval))

    if conn: conn.close()

if __name__ == "__main__":
    main()
