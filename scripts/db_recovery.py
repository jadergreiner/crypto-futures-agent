"""
Database recovery from corruption.
Runs when health_check detects integrity issues.

Recovery procedure:
1. Verify corruption (PRAGMA integrity_check)
2. Backup corrupted DB
3. Find latest good backup
4. Restore from backup
5. Sync missing data (last 10 candles)
"""

import sys
import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime
from subprocess import run, CalledProcessError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


def recover_database(
    db_path: str = "data/agent.db",
    backup_dir: str = "backups",
    workspace: str = ".",
) -> int:
    """
    Recover corrupted database from backup.
    
    Args:
        db_path: Path to corrupted database
        backup_dir: Directory containing backups
        workspace: Workspace root for sync script
    
    Returns:
        0 on success, 1 on failure
    """
    
    logger.info("=" * 70)
    logger.info("🚨 DATABASE RECOVERY INITIATED")
    logger.info(f"   Database: {db_path}")
    logger.info(f"   Backups: {backup_dir}")
    logger.info("=" * 70)
    
    try:
        # ===== STEP 1: DETECT CORRUPTION =====
        logger.info("\n[1/5] Detecting corruption...")
        
        db_path_obj = Path(db_path)
        
        if not db_path_obj.exists():
            logger.error(f"❌ Database not found: {db_path}")
            return 1
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            
            if result == "ok":
                logger.info("✅ Integrity check PASSED - no corruption detected")
                return 0
            else:
                logger.error(f"❌ Corruption detected: {result}")
        
        except Exception as e:
            logger.error(f"❌ Cannot open database: {str(e)}")
        
        # ===== STEP 2: BACKUP CORRUPTED STATE =====
        logger.info("\n[2/5] Backing up corrupted database...")
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        corrupted_backup = Path(backup_dir) / f"agent_corrupted_{timestamp}.db"
        
        try:
            corrupted_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, corrupted_backup)
            logger.info(f"✅ Corrupted DB backed up: {corrupted_backup}")
        except Exception as e:
            logger.error(f"❌ Failed to backup corrupted DB: {str(e)}")
            return 1
        
        # ===== STEP 3: FIND LATEST GOOD BACKUP =====
        logger.info("\n[3/5] Finding latest good backup...")
        
        backup_path_obj = Path(backup_dir)
        
        if not backup_path_obj.exists():
            logger.error(f"❌ Backup directory not found: {backup_dir}")
            logger.error("🚨 CANNOT RECOVER - no backups available")
            return 1
        
        # Find all backup files (excluding corrupted)
        backup_files = [
            f for f in backup_path_obj.glob("agent_backup_*.db")
            if not f.name.startswith("agent_corrupted_")
        ]
        
        if not backup_files:
            logger.error("❌ No valid backups found")
            logger.error("🚨 CANNOT RECOVER - escalate to manual intervention")
            return 1
        
        # Sort by modification time, newest first
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Find first uncorrupted backup
        good_backup = None
        for backup_file in backup_files:
            logger.info(f"   Checking: {backup_file.name}")
            
            try:
                conn = sqlite3.connect(backup_file)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                conn.close()
                
                if result == "ok":
                    logger.info(f"   ✅ Valid backup: {backup_file.name}")
                    good_backup = backup_file
                    break
                else:
                    logger.warning(f"   ❌ Backup also corrupted: {backup_file.name}")
            
            except Exception as e:
                logger.warning(f"   ❌ Cannot check backup: {str(e)}")
        
        if not good_backup:
            logger.error("❌ No uncorrupted backup found")
            logger.error("🚨 CANNOT RECOVER - all backups are corrupted")
            return 1
        
        logger.info(f"✅ Good backup found: {good_backup}")
        
        # ===== STEP 4: RESTORE FROM BACKUP =====
        logger.info("\n[4/5] Restoring from backup...")
        
        try:
            # Restore to temp file first
            temp_db = Path(db_path).with_suffix(".db.temp")
            shutil.copy2(good_backup, temp_db)
            
            # Verify restored DB
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ohlcv_h4")
            count = cursor.fetchone()[0]
            conn.close()
            
            logger.info(f"✅ Restored DB has {count} H4 candles")
            
            # Atomically replace
            shutil.move(temp_db, db_path)
            logger.info(f"✅ Database restored from {good_backup.name}")
        
        except Exception as e:
            logger.error(f"❌ Restore failed: {str(e)}")
            return 1
        
        # ===== STEP 5: SYNC MISSING DATA =====
        logger.info("\n[5/5] Syncing missing data...")
        
        try:
            logger.info("   Fetching last 10 candles to cover backup gap...")
            
            # Run sync job (fallback to manual if it fails)
            try:
                result = run(
                    [
                        sys.executable,
                        "-m", "scripts.daily_candle_sync",
                        "--workspace", workspace,
                        "--symbols", "all",
                        "--lookback", "10",
                        "--mode", "incremental"
                    ],
                    cwd=workspace,
                    timeout=600,  # 10 minutes
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info("✅ Sync completed successfully")
                else:
                    logger.warning(f"⚠️  Sync returned non-zero: {result.returncode}")
                    logger.warning("    Data may be slightly incomplete")
            
            except CalledProcessError as e:
                logger.warning(f"⚠️  Sync script error: {str(e)}")
                logger.warning("    Data gap may exist (< 2h)")
            
            except Exception as e:
                logger.warning(f"⚠️  Sync failed: {str(e)}")
                logger.warning("    Run manually: python3 -m scripts.daily_candle_sync ...")
        
        except Exception as e:
            logger.error(f"❌ Sync error: {str(e)}")
            # Don't fail recovery, just warn
        
        # ===== FINAL VERIFICATION =====
        logger.info("\n" + "=" * 70)
        logger.info("✅ DATABASE RECOVERY COMPLETE")
        
        db_size_mb = Path(db_path).stat().st_size / (1024 ** 2)
        logger.info(f"   New DB: {db_size_mb:.1f}MB")
        logger.info(f"   Backup: {good_backup.name}")
        
        logger.info("\n📊 NEXT STEPS:")
        logger.info("   1. Run: python3 scripts/health_check.py")
        logger.info("   2. Verify all metrics are green")
        logger.info("   3. Monitor next sync (01:00 UTC)")
        logger.info("   4. Review logs for root cause")
        
        logger.info("=" * 70)
        
        return 0
    
    except Exception as e:
        logger.critical(f"💥 UNHANDLED ERROR: {str(e)}")
        import traceback
        logger.critical(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = recover_database()
    sys.exit(exit_code)
