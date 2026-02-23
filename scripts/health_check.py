"""
Health check script: Verify data pipeline freshness, DB integrity, backup status.
Run manually or via cron (e.g., every 6 hours).

Checks 6 core metrics and returns exit code 0 (healthy) or 1 (issues).
"""

import sys
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta


def check_health(db_path: str = "data/agent.db", backup_dir: str = "backups") -> int:
    """
    Run 6-point health check on data pipeline.
    
    Returns:
        0 if healthy, 1 if issues found
    """
    
    issues = []
    
    print("\n" + "=" * 70)
    print("🏥 DATA PIPELINE HEALTH CHECK")
    print("=" * 70)
    
    # ===== CHECK 1: Database Connection & Freshness =====
    print("\n[1/6] Database Freshness...")
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        issues.append("DB_NOT_FOUND")
        return 1
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get last candle timestamp
        cursor.execute("SELECT MAX(timestamp) FROM ohlcv_h4 LIMIT 1")
        result = cursor.fetchone()
        
        if result is None or result[0] is None:
            print("❌ No data in database")
            issues.append("DB_EMPTY")
        else:
            last_ts = result[0]
            # Timestamp is in milliseconds
            last_sync_age_seconds = (datetime.utcnow().timestamp() * 1000 - last_ts) / 1000
            last_sync_age_hours = last_sync_age_seconds / 3600
            
            if last_sync_age_hours < 26:
                print(f"✅ Data freshness: {last_sync_age_hours:.1f}h old (target: <26h)")
            else:
                print(f"❌ Data is STALE: {last_sync_age_hours:.1f}h old (threshold: 26h)")
                issues.append("DATA_STALE")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        issues.append(f"DB_ERROR: {str(e)}")
        return 1
    
    # ===== CHECK 2: Symbol Coverage =====
    print("\n[2/6] Symbol Coverage...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM ohlcv_h4")
        symbol_count = cursor.fetchone()[0]
        target_symbols = 60
        
        if symbol_count >= target_symbols:
            print(f"✅ Symbols in DB: {symbol_count}/{target_symbols}")
        else:
            print(f"⚠️  Incomplete coverage: {symbol_count}/{target_symbols}")
            issues.append(f"MISSING_SYMBOLS: {target_symbols - symbol_count}")
        
        # Check for underrepresented symbols
        cursor.execute("""
            SELECT symbol, COUNT(*) as cnt 
            FROM ohlcv_h4 
            GROUP BY symbol 
            ORDER BY cnt ASC 
            LIMIT 5
        """)
        
        undersized = []
        for sym, cnt in cursor.fetchall():
            if cnt < 50:
                undersized.append(f"{sym}({cnt})")
        
        if undersized:
            print(f"⚠️  Symbols with <50 records: {', '.join(undersized[:3])}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Symbol check failed: {str(e)}")
        issues.append(f"SYMBOL_CHECK_ERROR: {str(e)}")
    
    # ===== CHECK 3: Database Integrity =====
    print("\n[3/6] Database Integrity...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # SQLite pragma integrity_check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            print(f"✅ Integrity check: PASSED")
        else:
            print(f"❌ Integrity check: FAILED")
            print(f"   Details: {result}")
            issues.append("INTEGRITY_FAILED")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Integrity check error: {str(e)}")
        issues.append(f"INTEGRITY_CHECK_ERROR: {str(e)}")
    
    # ===== CHECK 4: Database Size =====
    print("\n[4/6] Database Size...")
    
    try:
        db_size_bytes = os.path.getsize(db_path)
        db_size_mb = db_size_bytes / (1024 ** 2)
        min_threshold_mb = 10
        
        if db_size_mb >= min_threshold_mb:
            print(f"✅ DB file size: {db_size_mb:.1f}MB")
        else:
            print(f"⚠️  DB file is small: {db_size_mb:.1f}MB (expected: >{min_threshold_mb}MB)")
            issues.append(f"DB_UNDERSIZED: {db_size_mb:.1f}MB")
        
    except Exception as e:
        print(f"❌ Size check error: {str(e)}")
        issues.append(f"SIZE_CHECK_ERROR: {str(e)}")
    
    # ===== CHECK 5: Backup Status =====
    print("\n[5/6] Backup Status...")
    
    backup_path = Path(backup_dir)
    
    if not backup_path.exists():
        print(f"❌ Backup directory not found: {backup_dir}")
        issues.append("NO_BACKUP_DIR")
    else:
        backup_files = list(backup_path.glob("**/*.db"))
        
        if not backup_files:
            print(f"❌ No backup files found in {backup_dir}")
            issues.append("NO_BACKUPS")
        else:
            latest_backup = max(backup_files, key=os.path.getctime)
            backup_age_seconds = time.time() - os.path.getctime(latest_backup)
            backup_age_hours = backup_age_seconds / 3600
            
            if backup_age_hours < 26:
                print(f"✅ Latest backup: {backup_age_hours:.1f}h old")
                print(f"   File: {latest_backup.name}")
            else:
                print(f"⚠️  Backup is stale: {backup_age_hours:.1f}h old")
                issues.append(f"BACKUP_STALE: {backup_age_hours:.1f}h")
            
            # Check backup file size
            backup_size_mb = latest_backup.stat().st_size / (1024 ** 2)
            if backup_size_mb >= 5:
                print(f"   Size: {backup_size_mb:.1f}MB ✅")
            else:
                print(f"   Size: {backup_size_mb:.1f}MB (⚠️  too small)")
    
    # ===== CHECK 6: Sync Job Status (via log mtime) =====
    print("\n[6/6] Recent Sync Activity...")
    
    log_dir = Path("/var/log/crypto-futures-agent")
    
    if not log_dir.exists():
        print(f"⚠️  Log directory not found: {log_dir}")
        print("    (This is OK on development machines)")
    else:
        log_files = list(log_dir.glob("daily_sync_*.log"))
        
        if log_files:
            latest_log = max(log_files, key=os.path.getctime)
            log_age_seconds = time.time() - os.path.getctime(latest_log)
            log_age_hours = log_age_seconds / 3600
            
            if log_age_hours < 26:
                print(f"✅ Latest sync log: {log_age_hours:.1f}h old")
                print(f"   File: {latest_log.name}")
                
                # Try to read last status from log
                try:
                    with open(latest_log, 'r') as f:
                        last_lines = f.readlines()[-5:]
                        if any("COMPLETE" in line for line in last_lines):
                            print(f"   Status: COMPLETE ✅")
                        elif any("FAILED" in line for line in last_lines):
                            print(f"   Status: FAILED ❌")
                            issues.append("LAST_SYNC_FAILED")
                except Exception:
                    pass
            else:
                print(f"⚠️  No recent sync logs ({log_age_hours:.1f}h old)")
                issues.append(f"NO_RECENT_LOGS: {log_age_hours:.1f}h")
        else:
            print(f"⚠️  No sync logs found in {log_dir}")
            print("    (This is OK if sync hasn't run yet)")
    
    # ===== SUMMARY =====
    print("\n" + "=" * 70)
    
    if issues:
        print(f"⚠️  ISSUES FOUND ({len(issues)})")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print("\n🚨 RECOMMEND: Check logs and run manual sync if needed")
        print("   Manual sync: python3 -m scripts.daily_candle_sync --workspace . --symbols all")
        print("=" * 70)
        return 1
    else:
        print("✅ ALL CHECKS PASSED")
        print("   Data pipeline is healthy")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    import time
    
    exit_code = check_health()
    sys.exit(exit_code)
