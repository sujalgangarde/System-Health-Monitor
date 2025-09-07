# System Health Monitor  

A lightweight, cross-platform (Linux/Windows) Python tool that monitors **CPU, memory, disk usage, and network activity**.  
It logs system performance to a rotating log file and can optionally save metrics in SQLite for later analysis.  

---

## ✨ Features  
- Monitor **CPU %, Memory %, Disk %, Network I/O**  
- **Configurable thresholds** for alerts (WARNING/ERROR)  
- **Rotating log files** (prevents unbounded growth)  
- Optional **SQLite storage** of metrics and events  
- Works on **Linux & Windows**  

---

## 🧰 Tech  
- Python 3.8+  
- `psutil` for system stats  
- SQLite (built-in) for optional storage  
- Logging with `RotatingFileHandler`  

---

## 📦 Quick Start  

### 1) Setup  
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
```  

### 2) Run (logs only)  
```bash
python system_monitor.py
```  

### 3) Run with custom thresholds & SQLite storage  
```bash
python system_monitor.py --interval 10 --cpu-th 85 --mem-th 85 --disk-th 90 --db monitor.db
```  

### 4) View logs  
```bash
ls -l logs/
tail -f logs/system_health.log   # Linux/macOS
```  

---

## ⚙️ CLI Usage  
```bash
python system_monitor.py [--interval SECONDS] [--duration SECONDS]
                         [--cpu-th PCT] [--mem-th PCT] [--disk-th PCT]
                         [--db PATH]
```  

**Common Arguments:**  
- `--interval` → Seconds between samples (default: 5)  
- `--duration` → Total run time (omit = run indefinitely)  
- `--cpu-th / --mem-th / --disk-th` → Thresholds for alerts  
- `--db` → Path to SQLite DB (optional)  

---

## 🧪 Example Output  
```
[2025-09-07 10:05:12] INFO     CPU: 23.0%, MEM: 45.2%, DISK: 67.1%, NET Δ Sent: 112 KB, Δ Recv: 530 KB
[2025-09-07 10:10:12] WARNING  High Memory Usage: 89.7%
[2025-09-07 10:15:12] ERROR    Disk Usage Critical: 95.4%
```  

---

## 🗃️ SQLite Schema  
- **metrics** → `ts, cpu_pct, mem_pct, disk_pct, net_sent, net_recv`  
- **events** → `ts, level, message`  
