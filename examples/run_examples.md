
# Run Examples

## 1) Default (5s interval, only logs)
```bash
python system_monitor.py
```

## 2) Tight interval, DB enabled
```bash
python system_monitor.py --interval 2 --db monitor.db
```

## 3) Bounded run for 1 minute, stricter thresholds
```bash
python system_monitor.py --interval 5 --duration 60 --cpu-th 70 --mem-th 75 --disk-th 85 --db monitor.db
```

## 4) Custom log location/rotation
```bash
python system_monitor.py --log-file /tmp/health.log --log-max-bytes 500000 --log-backups 3
```
