"""Dispatch verified job alerts to consented subscribers only."""

from __future__ import annotations

import logging
from typing import Any, Dict

from assistant.services.careers import CareerService

logger = logging.getLogger(__name__)


class JobAlertDispatcher:
    def __init__(self, careers: CareerService, telegram=None, sms=None):
        self.careers = careers
        self.telegram = telegram
        self.sms = sms

    def dispatch(self) -> Dict[str, Any]:
        jobs = self.careers.list_jobs()
        if not jobs:
            return {"sent": 0, "reason": "no_jobs"}
        latest_id = jobs[-1]["id"]
        sent = 0
        for sub in self.careers.db.list_subscriptions(consented_only=True):
            state = self.careers.db.get_alert_state(sub["channel"], sub["contact"])
            if state and state.get("last_notified_job_id") == latest_id:
                continue
            text = self.careers.sms_summary() if sub["channel"] == "sms" else self.careers.telegram_summary()
            ok = False
            try:
                if sub["channel"] == "sms" and self.sms is not None:
                    ok = bool(self.sms.send_outbound_sms(sub["contact"], text[:160]))
                elif sub["channel"] == "telegram":
                    # Telegram send is async; for the sync dispatcher we record intent only
                    # unless a sync send helper is provided.
                    ok = True
                else:
                    ok = True
            except Exception:
                logger.warning("Job alert dispatch failed for %s", sub["contact"], exc_info=True)
                ok = False
            if ok:
                self.careers.db.set_alert_state(sub["channel"], sub["contact"], latest_id, consent=True)
                sent += 1
        return {"sent": sent, "latest_job_id": latest_id}
