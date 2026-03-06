"""
transactions/fine_sync.py
─────────────────────────
Background daemon that runs every SYNC_INTERVAL_SECONDS (default 60 s).

Each cycle does two things:
  1. Flip issued → overdue for all past-due transactions
     (Transaction.sync_overdue_for_library — existing behaviour).
  2. Create or update a Fine row for every active overdue transaction
     so the amount is always persisted in the DB and stays current.

Fine row upsert rules
─────────────────────
  • One Fine row per transaction per fine_type.
  • Only unpaid fines are updated — paid/waived rows are never touched.
  • Amount = overdue_days × fine_rate_per_day  (live rate from rules).
  • If the transaction is no longer overdue the fine row is left as-is
    (amount frozen at the day it was returned / cleared).

Override the sync interval in settings.py:
    FINE_SYNC_INTERVAL = 300   # every 5 minutes (default: 60)
"""

import logging
import os
import threading
import time
from datetime import date
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger("transactions.fine_sync")

# ── Module-level guard — only one thread per process ─────────────────────────
_sync_thread: threading.Thread | None = None
_started = False
_lock    = threading.Lock()

SYNC_INTERVAL_SECONDS: int = int(getattr(settings, "FINE_SYNC_INTERVAL", 60))


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — flip issued → overdue  (existing logic, unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def _sync_overdue_status(library, Transaction) -> None:
    """Bulk-flip issued → overdue and keep fine_rate_per_day in sync."""
    Transaction.sync_overdue_for_library(library)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — persist Fine rows for every overdue transaction
# ─────────────────────────────────────────────────────────────────────────────

def _sync_fine_amounts(library, Transaction, Fine) -> int:
    """
    For every active (issued/overdue) transaction that has accrued a fine,
    create or update an unpaid Fine row so the amount is always in the DB.

    Returns the number of Fine rows created or updated.
    """
    from django.db import transaction as db_tx

    today = date.today()

    # All active loans that have accrued any fine amount
    active_txns = (
        Transaction.objects
        .for_library(library)
        .filter(status__in=(Transaction.STATUS_OVERDUE, Transaction.STATUS_ISSUED))
        .select_related("transaction_ptr" if False else None)  # no-op, just clarity
    )

    touched = 0

    for txn in active_txns:
        overdue_fine  = txn.overdue_fine    # Decimal, computed @property
        damage_charge = txn.damage_charge   # stored field

        # ── Overdue fine row ──────────────────────────────────────────────
        if overdue_fine > Decimal("0.00"):
            try:
                with db_tx.atomic():
                    fine_obj, created = Fine.objects.get_or_create(
                        library     = library,
                        transaction = txn,
                        fine_type   = Fine.TYPE_OVERDUE,
                        defaults={
                            "amount": overdue_fine,
                            "status": Fine.STATUS_UNPAID,
                        },
                    )
                    if not created and fine_obj.status == Fine.STATUS_UNPAID:
                        # Update amount only if it has changed
                        if fine_obj.amount != overdue_fine:
                            fine_obj.amount = overdue_fine
                            fine_obj.save(update_fields=["amount", "updated_at"])
                    touched += 1
            except Exception as exc:
                logger.warning(
                    "fine_sync: could not upsert overdue fine for txn %s: %s",
                    txn.pk, exc,
                )

        # ── Damage charge row (only if not already created at return) ─────
        if damage_charge > Decimal("0.00"):
            try:
                with db_tx.atomic():
                    fine_obj, created = Fine.objects.get_or_create(
                        library     = library,
                        transaction = txn,
                        fine_type   = Fine.TYPE_DAMAGE,
                        defaults={
                            "amount": damage_charge,
                            "status": Fine.STATUS_UNPAID,
                        },
                    )
                    if not created and fine_obj.status == Fine.STATUS_UNPAID:
                        if fine_obj.amount != damage_charge:
                            fine_obj.amount = damage_charge
                            fine_obj.save(update_fields=["amount", "updated_at"])
                    touched += 1
            except Exception as exc:
                logger.warning(
                    "fine_sync: could not upsert damage fine for txn %s: %s",
                    txn.pk, exc,
                )

    return touched


# ─────────────────────────────────────────────────────────────────────────────
# Combined sync — called every cycle
# ─────────────────────────────────────────────────────────────────────────────

def _run_sync_once() -> int:
    """
    Full sync pass: overdue status flip + Fine row upserts for all libraries.
    Returns the number of libraries processed.
    """
    from accounts.models import Library
    from finance.models import Fine
    from .models import Transaction

    libraries = list(Library.objects.all())
    synced = 0

    for library in libraries:
        try:
            _sync_overdue_status(library, Transaction)
            touched = _sync_fine_amounts(library, Transaction, Fine)
            logger.debug(
                "fine_sync: library %s — %d fine row(s) created/updated.",
                getattr(library, "name", library.pk),
                touched,
            )
            synced += 1
        except Exception as exc:
            logger.warning(
                "fine_sync: error syncing library %s (pk=%s): %s",
                getattr(library, "name", "?"),
                library.pk,
                exc,
            )

    return synced


# ─────────────────────────────────────────────────────────────────────────────
# Background thread
# ─────────────────────────────────────────────────────────────────────────────

def _sync_loop() -> None:
    logger.info(
        "fine_sync: background thread started (PID %s, interval %ss).",
        os.getpid(),
        SYNC_INTERVAL_SECONDS,
    )
    while True:
        time.sleep(SYNC_INTERVAL_SECONDS)
        try:
            count = _run_sync_once()
            logger.debug(
                "fine_sync: synced %d librar%s.",
                count,
                "y" if count == 1 else "ies",
            )
        except Exception as exc:
            logger.exception("fine_sync: unexpected error in sync loop: %s", exc)


def start_auto_sync() -> None:
    """
    Start the background sync thread (safe to call multiple times).
    Call this from TransactionsConfig.ready().
    """
    global _sync_thread, _started

    with _lock:
        if _started:
            return
        _started = True

    _sync_thread = threading.Thread(
        target=_sync_loop,
        name="fine-auto-sync",
        daemon=True,
    )
    _sync_thread.start()
    logger.info(
        "fine_sync: daemon thread '%s' launched (interval=%ss).",
        _sync_thread.name,
        SYNC_INTERVAL_SECONDS,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Manual trigger
# ─────────────────────────────────────────────────────────────────────────────

def run_sync_now() -> int:
    """
    Run the full sync immediately (blocking).
    Useful from the shell or management commands:
        from transactions.fine_sync import run_sync_now
        run_sync_now()
    """
    count = _run_sync_once()
    logger.info(
        "fine_sync: manual run — synced %d librar%s.",
        count, "y" if count == 1 else "ies",
    )
    return count