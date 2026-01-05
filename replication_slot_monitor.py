"""Replication Slot Health Monitoring for PostgreSQL.

This module monitors PostgreSQL replication slots and alerts when:
- A slot becomes inactive (disconnected)
- A slot's lag grows beyond configured thresholds
- A slot has been inactive for too long

Default Thresholds:
    - WARNING:  100 MB lag (restart_lsn behind current WAL)
    - CRITICAL: 500 MB lag
    
    Note: A small lag (e.g., 10-50 MB) is NORMAL and represents the replication
    buffer/checkpoint margin. This is NOT unprocessed data - it's a safety buffer
    for crash recovery. Only alert when lag grows significantly beyond this baseline.

CLI Usage:
    # Check Snowflake PostgreSQL (default thresholds: warning=100MB, critical=500MB)
    uv run python replication_slot_monitor.py
    
    # Check Crunchy Bridge
    uv run python replication_slot_monitor.py --crunchy
    
    # Check both databases
    uv run python replication_slot_monitor.py --all
    
    # Custom thresholds (in MB)
    uv run python replication_slot_monitor.py --warning 50 --critical 200

Testing the Failure Mechanism:
    # Use very low thresholds to FORCE a failure (for testing Prefect automations)
    uv run python replication_slot_monitor.py --warning 1 --critical 5
    
    # This will fail because even healthy slots have ~10-20 MB baseline lag,
    # which exceeds the 5 MB critical threshold. Use this to verify your
    # Prefect automation triggers correctly on flow failures.

Prefect Deployment:
    uv run prefect deployment run 'monitor-replication-slots/replication-slot-monitor'

Prefect Automation Setup:
    1. Go to Prefect UI → Automations → Create Automation
    2. Trigger: Flow run state = "Failed"
    3. Filter by deployment: "replication-slot-monitor" (optional)
    4. Action: Send notification (email, Slack, etc.)

Email Setup (Optional - alternative to Prefect automations):
    # Install email support
    uv add prefect-email
    
    # Create email credentials block
    from prefect_email import EmailServerCredentials
    credentials = EmailServerCredentials(
        username="your-email@gmail.com",
        password="your-app-password",  # Use App Password for Gmail
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_type="STARTTLS",
    )
    credentials.save("email-creds", overwrite=True)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from prefect import flow, task, get_run_logger

from crunchy_bridge_connection.connection import get_connection


class SlotStatus(Enum):
    """Health status of a replication slot."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DISCONNECTED = "disconnected"


@dataclass
class SlotHealth:
    """Health information for a replication slot."""
    slot_name: str
    active: bool
    lag_bytes: int
    lag_pretty: str
    unconfirmed_bytes: int
    unconfirmed_pretty: str
    status: SlotStatus
    message: str


# Threshold configuration (in bytes)
WARNING_LAG_BYTES = 100 * 1024 * 1024      # 100 MB
CRITICAL_LAG_BYTES = 500 * 1024 * 1024     # 500 MB
WARNING_UNCONFIRMED_BYTES = 50 * 1024 * 1024   # 50 MB


SLOT_HEALTH_QUERY = """
SELECT 
    slot_name,
    active,
    COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn), 0) AS lag_bytes,
    pg_size_pretty(COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn), 0)) AS lag_pretty,
    COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn), 0) AS unconfirmed_bytes,
    pg_size_pretty(COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn), 0)) AS unconfirmed_pretty,
    slot_type,
    plugin
FROM pg_replication_slots
ORDER BY lag_bytes DESC;
"""


@task(name="check-replication-slots")
def check_replication_slots(
    crunchy_or_snowflake: str = "snowflake",
    warning_lag_mb: int = 100,
    critical_lag_mb: int = 500,
    warning_unconfirmed_mb: int = 50,
) -> list[SlotHealth]:
    """Check all replication slots and return their health status.
    
    Args:
        crunchy_or_snowflake: Which database to check ("crunchy" or "snowflake")
        warning_lag_mb: Warning threshold for restart_lsn lag in MB
        critical_lag_mb: Critical threshold for restart_lsn lag in MB
        warning_unconfirmed_mb: Warning threshold for unconfirmed data in MB
    
    Returns:
        List of SlotHealth objects for each replication slot
    """
    logger = get_run_logger()
    
    warning_lag = warning_lag_mb * 1024 * 1024
    critical_lag = critical_lag_mb * 1024 * 1024
    warning_unconfirmed = warning_unconfirmed_mb * 1024 * 1024
    
    db_name = "Crunchy Bridge" if crunchy_or_snowflake == "crunchy" else "Snowflake"
    logger.info(f"Checking replication slots on {db_name}...")
    
    slots: list[SlotHealth] = []
    
    try:
        with get_connection(crunchy_or_snowflake=crunchy_or_snowflake) as conn:
            with conn.cursor() as cur:
                cur.execute(SLOT_HEALTH_QUERY)
                rows = cur.fetchall()
                
                if not rows:
                    logger.info("No replication slots found.")
                    return slots
                
                for row in rows:
                    slot_name, active, lag_bytes, lag_pretty, unconfirmed_bytes, unconfirmed_pretty, slot_type, plugin = row
                    
                    # Determine status
                    if not active:
                        status = SlotStatus.DISCONNECTED
                        message = f"Slot is DISCONNECTED with {lag_pretty} lag"
                    elif lag_bytes >= critical_lag:
                        status = SlotStatus.CRITICAL
                        message = f"CRITICAL: Lag at {lag_pretty} (threshold: {critical_lag_mb}MB)"
                    elif lag_bytes >= warning_lag:
                        status = SlotStatus.WARNING
                        message = f"WARNING: Lag at {lag_pretty} (threshold: {warning_lag_mb}MB)"
                    elif unconfirmed_bytes >= warning_unconfirmed:
                        status = SlotStatus.WARNING
                        message = f"WARNING: Unconfirmed data at {unconfirmed_pretty}"
                    else:
                        status = SlotStatus.HEALTHY
                        message = f"Healthy: lag={lag_pretty}, unconfirmed={unconfirmed_pretty}"
                    
                    slot_health = SlotHealth(
                        slot_name=slot_name,
                        active=active,
                        lag_bytes=lag_bytes,
                        lag_pretty=lag_pretty,
                        unconfirmed_bytes=unconfirmed_bytes,
                        unconfirmed_pretty=unconfirmed_pretty,
                        status=status,
                        message=message,
                    )
                    slots.append(slot_health)
                    
                    # Log status with appropriate level
                    status_emoji = {
                        SlotStatus.HEALTHY: "✅",
                        SlotStatus.WARNING: "⚠️",
                        SlotStatus.CRITICAL: "🚨",
                        SlotStatus.DISCONNECTED: "❌",
                    }
                    logger.info(f"{status_emoji[status]} {slot_name}: {message}")
                
    except Exception as e:
        logger.error(f"Failed to check replication slots: {e}")
        raise
    
    return slots


@task(name="send-email-alert")
def send_email_alert(
    slots: list[SlotHealth],
    database_name: str,
    email_credentials_block: str = "email-creds",
    to_emails: list[str] | None = None,
) -> bool:
    """Send email alert for unhealthy slots.
    
    Args:
        slots: List of SlotHealth objects
        database_name: Name of the database being monitored
        email_credentials_block: Name of the Prefect EmailServerCredentials block
        to_emails: List of recipient email addresses
    
    Returns:
        True if alert was sent, False otherwise
    """
    logger = get_run_logger()
    
    # Filter to only problematic slots
    problem_slots = [s for s in slots if s.status != SlotStatus.HEALTHY]
    
    if not problem_slots:
        logger.info("All slots healthy, no alert needed.")
        return False
    
    if not to_emails:
        logger.warning("No recipient emails configured. Set 'to_emails' parameter.")
        return False
    
    # Build alert message
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Determine overall severity
    has_critical = any(s.status == SlotStatus.CRITICAL for s in problem_slots)
    has_disconnected = any(s.status == SlotStatus.DISCONNECTED for s in problem_slots)
    
    if has_critical or has_disconnected:
        severity = "🚨 CRITICAL"
        severity_plain = "CRITICAL"
    else:
        severity = "⚠️ WARNING"
        severity_plain = "WARNING"
    
    subject = f"[{severity_plain}] PostgreSQL Replication Slot Alert - {database_name}"
    
    # Build HTML email body
    html_rows = ""
    for slot in problem_slots:
        status_emoji = {
            SlotStatus.WARNING: "⚠️",
            SlotStatus.CRITICAL: "🚨",
            SlotStatus.DISCONNECTED: "❌",
        }.get(slot.status, "❓")
        
        status_color = {
            SlotStatus.WARNING: "#f59e0b",
            SlotStatus.CRITICAL: "#dc2626",
            SlotStatus.DISCONNECTED: "#7c3aed",
        }.get(slot.status, "#6b7280")
        
        html_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                <strong>{slot.slot_name}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                <span style="background-color: {status_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                    {status_emoji} {slot.status.value.upper()}
                </span>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{slot.active}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;"><strong>{slot.lag_pretty}</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{slot.unconfirmed_pretty}</td>
        </tr>
        """
    
    html_body = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
        <div style="background-color: {'#fef2f2' if has_critical or has_disconnected else '#fffbeb'}; border-left: 4px solid {'#dc2626' if has_critical or has_disconnected else '#f59e0b'}; padding: 16px; margin-bottom: 20px;">
            <h2 style="margin: 0 0 8px 0; color: #111827;">{severity} PostgreSQL Replication Slot Alert</h2>
            <p style="margin: 0; color: #6b7280;">Database: <strong>{database_name}</strong> | Time: {timestamp}</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <thead>
                <tr style="background-color: #f9fafb;">
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;">Slot Name</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;">Status</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;">Active</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;">Lag</th>
                    <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e7eb;">Unconfirmed</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>
        
        <div style="margin-top: 20px; padding: 16px; background-color: #f3f4f6; border-radius: 8px;">
            <h3 style="margin: 0 0 8px 0; font-size: 14px; color: #374151;">What This Means:</h3>
            <ul style="margin: 0; padding-left: 20px; color: #6b7280; font-size: 14px;">
                <li><strong>DISCONNECTED</strong>: Replication consumer is not connected. WAL files are accumulating.</li>
                <li><strong>CRITICAL</strong>: Lag exceeds critical threshold. Disk space may be at risk.</li>
                <li><strong>WARNING</strong>: Lag is elevated. Monitor closely.</li>
            </ul>
        </div>
        
        <p style="margin-top: 20px; font-size: 12px; color: #9ca3af;">
            This alert was sent by the Prefect replication slot monitor.
        </p>
    </body>
    </html>
    """
    
    # Plain text fallback
    text_body = f"""
{severity} PostgreSQL Replication Slot Alert
Database: {database_name}
Time: {timestamp}

PROBLEMATIC SLOTS:
"""
    for slot in problem_slots:
        text_body += f"""
- {slot.slot_name}
  Status: {slot.status.value.upper()}
  Active: {slot.active}
  Lag: {slot.lag_pretty}
  Unconfirmed: {slot.unconfirmed_pretty}
  Message: {slot.message}
"""
    
    try:
        from prefect_email import EmailServerCredentials, email_send_message
        
        credentials = EmailServerCredentials.load(email_credentials_block)
        
        email_send_message(
            email_server_credentials=credentials,
            subject=subject,
            msg=html_body,
            msg_plain=text_body,
            email_to=to_emails,
        )
        
        logger.info(f"Email alert sent to {to_emails} for {len(problem_slots)} problematic slot(s).")
        return True
        
    except ImportError:
        logger.error(
            "prefect-email not installed. Install with:\n"
            "  uv add prefect-email"
        )
        return False
    except ValueError:
        logger.warning(
            f"EmailServerCredentials block '{email_credentials_block}' not found.\n"
            "Create one with:\n"
            "  from prefect_email import EmailServerCredentials\n"
            "  creds = EmailServerCredentials(\n"
            "      username='your-email@gmail.com',\n"
            "      password='your-app-password',\n"
            "      smtp_server='smtp.gmail.com',\n"
            "      smtp_port=587,\n"
            "      smtp_type='STARTTLS',\n"
            "  )\n"
            "  creds.save('email-creds')"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        return False


@task(name="log-summary")
def log_summary(slots: list[SlotHealth], database_name: str) -> dict:
    """Log a summary of slot health and return metrics.
    
    Returns:
        Dictionary with health metrics for Prefect artifacts
    """
    logger = get_run_logger()
    
    total = len(slots)
    healthy = sum(1 for s in slots if s.status == SlotStatus.HEALTHY)
    warning = sum(1 for s in slots if s.status == SlotStatus.WARNING)
    critical = sum(1 for s in slots if s.status == SlotStatus.CRITICAL)
    disconnected = sum(1 for s in slots if s.status == SlotStatus.DISCONNECTED)
    
    max_lag = max((s.lag_bytes for s in slots), default=0)
    max_lag_pretty = max((s.lag_pretty for s in slots), default="0 bytes") if slots else "N/A"
    
    summary = f"""
╔══════════════════════════════════════════════════════════╗
║           REPLICATION SLOT HEALTH SUMMARY                ║
║                    {database_name:^20}                  ║
╠══════════════════════════════════════════════════════════╣
║  Total Slots:      {total:>5}                              ║
║  ✅ Healthy:       {healthy:>5}                              ║
║  ⚠️  Warning:       {warning:>5}                              ║
║  🚨 Critical:      {critical:>5}                              ║
║  ❌ Disconnected:  {disconnected:>5}                              ║
╠══════════════════════════════════════════════════════════╣
║  Max Lag:          {max_lag_pretty:>10}                         ║
╚══════════════════════════════════════════════════════════╝
"""
    logger.info(summary)
    
    return {
        "database": database_name,
        "total_slots": total,
        "healthy": healthy,
        "warning": warning,
        "critical": critical,
        "disconnected": disconnected,
        "max_lag_bytes": max_lag,
        "has_problems": (warning + critical + disconnected) > 0,
    }


class ReplicationSlotAlert(Exception):
    """Raised when replication slots have problems (for Prefect automation triggers)."""
    pass


@flow(name="monitor-replication-slots", log_prints=True)
def monitor_replication_slots(
    crunchy_or_snowflake: str = "snowflake",
    warning_lag_mb: int = 100,
    critical_lag_mb: int = 500,
    warning_unconfirmed_mb: int = 50,
    fail_on_problems: bool = True,
    send_email: bool = False,
    email_credentials_block: str = "email-creds",
    alert_emails: list[str] | None = None,
) -> dict:
    """Monitor PostgreSQL replication slots and alert on issues.
    
    Args:
        crunchy_or_snowflake: Which database to monitor ("crunchy" or "snowflake")
        warning_lag_mb: Warning threshold for lag in MB (default: 100)
        critical_lag_mb: Critical threshold for lag in MB (default: 500)
        warning_unconfirmed_mb: Warning threshold for unconfirmed data in MB (default: 50)
        fail_on_problems: If True, raise exception on any problems (for Prefect automations)
        send_email: Whether to send email alerts for problems
        email_credentials_block: Name of Prefect EmailServerCredentials block
        alert_emails: List of email addresses to send alerts to
    
    Returns:
        Dictionary with health metrics
        
    Raises:
        ReplicationSlotAlert: When fail_on_problems=True and slots have issues
    """
    db_name = "Crunchy Bridge" if crunchy_or_snowflake == "crunchy" else "Snowflake"
    
    # Check all slots
    slots = check_replication_slots(
        crunchy_or_snowflake=crunchy_or_snowflake,
        warning_lag_mb=warning_lag_mb,
        critical_lag_mb=critical_lag_mb,
        warning_unconfirmed_mb=warning_unconfirmed_mb,
    )
    
    # Log summary
    metrics = log_summary(slots, db_name)
    
    # Send email alerts if enabled and there are problems
    if send_email and metrics["has_problems"] and alert_emails:
        send_email_alert(slots, db_name, email_credentials_block, alert_emails)
    
    # Fail the flow if there are problems (triggers Prefect automation)
    if fail_on_problems and metrics["has_problems"]:
        problem_slots = [s for s in slots if s.status != SlotStatus.HEALTHY]
        error_details = "\n".join([
            f"  - {s.slot_name}: {s.status.value.upper()} (lag: {s.lag_pretty})"
            for s in problem_slots
        ])
        raise ReplicationSlotAlert(
            f"Replication slot issues detected on {db_name}!\n"
            f"Problematic slots:\n{error_details}"
        )
    
    return metrics


@flow(name="monitor-all-replication-slots", log_prints=True)
def monitor_all_replication_slots(
    warning_lag_mb: int = 100,
    critical_lag_mb: int = 500,
    warning_unconfirmed_mb: int = 50,
    fail_on_problems: bool = True,
    send_email: bool = False,
    email_credentials_block: str = "email-creds",
    alert_emails: list[str] | None = None,
) -> dict:
    """Monitor replication slots on ALL configured databases.
    
    Checks both Crunchy Bridge and Snowflake PostgreSQL instances.
    
    Args:
        fail_on_problems: If True, raise exception after checking all DBs if any have problems
    
    Returns:
        Dictionary with combined metrics from all databases
        
    Raises:
        ReplicationSlotAlert: When fail_on_problems=True and any database has slot issues
    """
    logger = get_run_logger()
    
    results = {}
    all_problems = []
    
    for db_type in ["snowflake", "crunchy"]:
        db_name = "Crunchy Bridge" if db_type == "crunchy" else "Snowflake"
        try:
            logger.info(f"\n{'='*60}\nChecking {db_name}...\n{'='*60}")
            # Don't fail individual checks - collect all results first
            metrics = monitor_replication_slots(
                crunchy_or_snowflake=db_type,
                warning_lag_mb=warning_lag_mb,
                critical_lag_mb=critical_lag_mb,
                warning_unconfirmed_mb=warning_unconfirmed_mb,
                fail_on_problems=False,  # Don't fail here, we'll aggregate
                send_email=send_email,
                email_credentials_block=email_credentials_block,
                alert_emails=alert_emails,
            )
            results[db_type] = metrics
            
            if metrics.get("has_problems"):
                all_problems.append(f"{db_name}: {metrics['warning'] + metrics['critical'] + metrics['disconnected']} problematic slot(s)")
                
        except Exception as e:
            logger.warning(f"Could not check {db_name}: {e}")
            results[db_type] = {"error": str(e)}
    
    # Fail after checking all databases if any had problems
    if fail_on_problems and all_problems:
        raise ReplicationSlotAlert(
            f"Replication slot issues detected!\n" + "\n".join(f"  - {p}" for p in all_problems)
        )
    
    return results


if __name__ == "__main__":
    # ==========================================================================
    # CLI USAGE
    # ==========================================================================
    #
    # Check Snowflake PostgreSQL (default):
    #   uv run python replication_slot_monitor.py
    #
    # Check Crunchy Bridge:
    #   uv run python replication_slot_monitor.py --crunchy
    #
    # Check both databases:
    #   uv run python replication_slot_monitor.py --all
    #
    # Custom thresholds (in MB):
    #   uv run python replication_slot_monitor.py --warning 50 --critical 200
    #
    # ==========================================================================
    
    import sys
    
    # Parse simple CLI args
    use_crunchy = "--crunchy" in sys.argv
    check_all = "--all" in sys.argv
    
    # Parse threshold args
    warning_mb = 100
    critical_mb = 500
    if "--warning" in sys.argv:
        idx = sys.argv.index("--warning")
        if idx + 1 < len(sys.argv):
            warning_mb = int(sys.argv[idx + 1])
    if "--critical" in sys.argv:
        idx = sys.argv.index("--critical")
        if idx + 1 < len(sys.argv):
            critical_mb = int(sys.argv[idx + 1])
    
    print(f"Thresholds: warning={warning_mb}MB, critical={critical_mb}MB\n")
    
    if check_all:
        monitor_all_replication_slots(
            warning_lag_mb=warning_mb,
            critical_lag_mb=critical_mb,
            fail_on_problems=True,  # Will raise exception on problems
            send_email=False,  # Disable email for local testing
        )
    else:
        db_type = "crunchy" if use_crunchy else "snowflake"
        monitor_replication_slots(
            crunchy_or_snowflake=db_type,
            warning_lag_mb=warning_mb,
            critical_lag_mb=critical_mb,
            fail_on_problems=True,  # Will raise exception on problems
            send_email=False,  # Disable email for local testing
        )

