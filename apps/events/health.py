"""
Automated AI Event Health Scoring Engine.

Computes a 0-100 health score for each event based on real data:
  - Budget utilization trajectory
  - Task completion rate
  - Staff assignment coverage
  - Vendor confirmation status
  - Days-until-event urgency
  - Approval workflow state

No OpenRouter call required — score is deterministic and instant.
OpenRouter is used only when generating the natural-language briefing.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone as dt_tz
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class EventHealthScore:
    event_id: int
    event_name: str
    score: int                    # 0-100
    grade: str                    # A / B / C / D / F
    color: str                    # CSS class: health-green / health-amber / health-red
    badge_css: str                # pill badge colour
    summary: str                  # one-line plain-English status
    factors: list[dict] = field(default_factory=list)   # breakdown items
    recommendations: list[str] = field(default_factory=list)

    @property
    def icon(self) -> str:
        if self.score >= 75:
            return "✅"
        if self.score >= 50:
            return "⚠️"
        return "🔴"


def compute_event_health(event) -> EventHealthScore:
    """
    Compute deterministic health score for a single Event instance.
    Cached in memory for 60 seconds per event version to eliminate N+1 bottlenecks.
    """
    from django.core.cache import cache
    from django.db.models import Count, Q, Sum

    event_id = getattr(event, "id", None)
    if not event_id:
        return EventHealthScore(
            event_id=0, event_name="", score=50, grade="C",
            color="health-amber", badge_css="badge-warning", summary="New event"
        )

    updated_val = getattr(event, "updated_at", None)
    updated_ts = int(updated_val.timestamp()) if (updated_val and hasattr(updated_val, "timestamp")) else 0
    cache_key = f"event_health_v2_{event_id}_{updated_ts}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached


    from apps.finance.models import ExpenseStatus
    from apps.operations.models import TaskStatus, AttendanceStatus
    from apps.vendors.models import VendorStatus
    from apps.events.models import EventStatus

    now = timezone.now()
    factors: list[dict] = []
    recommendations: list[str] = []

    # ── 1. Workflow state (20 pts) ────────────────────────────────────────────
    status_scores = {
        EventStatus.DRAFT: 10,
        EventStatus.SUBMITTED: 14,
        EventStatus.REJECTED: 2,
        EventStatus.APPROVED: 18,
        EventStatus.IN_PROGRESS: 20,
        EventStatus.COMPLETED: 20,
        EventStatus.CANCELLED: 0,
    }
    workflow_score = status_scores.get(event.status, 10)
    factors.append({
        "label": "Workflow State",
        "score": workflow_score,
        "max": 20,
        "detail": event.get_status_display(),
    })
    if event.status == EventStatus.DRAFT:
        recommendations.append("Submit the event for admin approval to unblock planning.")
    if event.status == EventStatus.REJECTED:
        recommendations.append(f"Address rejection reason and resubmit: {event.rejection_reason or 'No reason given'}.")

    # ── 2. Budget utilisation (25 pts) ───────────────────────────────────────
    budget = event.budget or Decimal("0")
    approved_expenses = event.expenses.filter(status=ExpenseStatus.APPROVED).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")

    if budget > 0:
        util_pct = float(approved_expenses / budget * 100)
    else:
        util_pct = 0.0

    if util_pct < 50:
        budget_score = 25
    elif util_pct < 80:
        budget_score = 20
    elif util_pct < 90:
        budget_score = 12
        recommendations.append(f"Budget at {util_pct:.0f}% — approaching critical threshold (90%).")
    elif util_pct < 100:
        budget_score = 5
        recommendations.append(f"Budget critical at {util_pct:.0f}%. Raise a change request immediately.")
    else:
        budget_score = 0
        recommendations.append("Budget exceeded! Initiate emergency financial review.")

    factors.append({
        "label": "Budget Utilisation",
        "score": budget_score,
        "max": 25,
        "detail": f"₹{approved_expenses:,.0f} / ₹{budget:,.0f} ({util_pct:.0f}%)",
    })

    # ── 3. Task completion (20 pts) ──────────────────────────────────────────
    task_agg = event.tasks.aggregate(
        total=Count("id"),
        done=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
        overdue=Count("id", filter=Q(status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS], due_date__lt=now))
    )
    total_tasks = task_agg["total"] or 0
    done_tasks = task_agg["done"] or 0
    overdue_tasks = task_agg["overdue"] or 0

    if total_tasks == 0:
        task_score = 10
        recommendations.append("No tasks created — add tasks to track execution.")
    else:
        completion_rate = done_tasks / total_tasks
        task_score = min(20, int(completion_rate * 20))
        if overdue_tasks:
            task_score = max(0, task_score - overdue_tasks * 3)
            recommendations.append(f"{overdue_tasks} task(s) are overdue — prioritise immediately.")

    factors.append({
        "label": "Task Completion",
        "score": task_score,
        "max": 20,
        "detail": f"{done_tasks}/{total_tasks} done" + (f", {overdue_tasks} overdue" if overdue_tasks else ""),
    })

    # ── 4. Staff assignment (15 pts) ─────────────────────────────────────────
    staff_count = event.staff_assignments.count()
    if staff_count == 0:
        staff_score = 2
        recommendations.append("No staff assigned — assign operational team before event date.")
    elif staff_count < 2:
        staff_score = 8
        recommendations.append("Assign additional staff for better operational coverage.")
    else:
        staff_score = 15

    factors.append({
        "label": "Staff Coverage",
        "score": staff_score,
        "max": 15,
        "detail": f"{staff_count} staff assigned",
    })

    # ── 5. Vendor status (10 pts) ────────────────────────────────────────────
    vendors = getattr(event, "vendor_assignments", None)
    if vendors is not None:
        vendor_agg = vendors.aggregate(
            total=Count("id"),
            confirmed=Count("id", filter=Q(status=VendorStatus.CONFIRMED))
        )
        total_vendors = vendor_agg["total"] or 0
        confirmed_vendors = vendor_agg["confirmed"] or 0
    else:
        total_vendors = 0
        confirmed_vendors = 0

    if total_vendors == 0:
        vendor_score = 7
    else:
        confirm_rate = confirmed_vendors / total_vendors
        vendor_score = min(10, int(confirm_rate * 10))
        if confirmed_vendors < total_vendors:
            unconfirmed = total_vendors - confirmed_vendors
            recommendations.append(f"{unconfirmed} vendor(s) not yet confirmed — follow up now.")

    factors.append({
        "label": "Vendor Confirmation",
        "score": vendor_score,
        "max": 10,
        "detail": f"{confirmed_vendors}/{total_vendors} confirmed" if total_vendors else "No vendors linked",
    })

    # ── 6. Time urgency (10 pts) ─────────────────────────────────────────────
    days_to_event = (event.start_date.replace(tzinfo=dt_tz.utc) - now.replace(tzinfo=dt_tz.utc)).days \
        if event.start_date.tzinfo is None else (event.start_date - now).days

    if days_to_event < 0:
        urgency_score = 10
    elif days_to_event <= 3:
        urgency_score = 2
        if event.status not in ("IN_PROGRESS", "COMPLETED"):
            recommendations.append(f"Event is in {days_to_event} day(s) — escalate all pending items immediately.")
    elif days_to_event <= 7:
        urgency_score = 5
    elif days_to_event <= 14:
        urgency_score = 8
    else:
        urgency_score = 10

    factors.append({
        "label": "Time Buffer",
        "score": urgency_score,
        "max": 10,
        "detail": f"{days_to_event} days until event" if days_to_event >= 0 else "Event has passed",
    })

    # ── Final score ───────────────────────────────────────────────────────────
    total = workflow_score + budget_score + task_score + staff_score + vendor_score + urgency_score

    if total >= 80:
        grade, color, badge_css = "A", "health-green", "badge-success"
        summary = "On track — all key indicators healthy."
    elif total >= 65:
        grade, color, badge_css = "B", "health-green", "badge-success"
        summary = "Generally healthy — minor items need attention."
    elif total >= 50:
        grade, color, badge_css = "C", "health-amber", "badge-warning"
        summary = "Moderate risk — several issues require follow-up."
    elif total >= 35:
        grade, color, badge_css = "D", "health-red", "badge-danger"
        summary = "High risk — immediate action required on multiple fronts."
    else:
        grade, color, badge_css = "F", "health-red", "badge-danger"
        summary = "Critical — event is at severe risk of failure."

    result = EventHealthScore(
        event_id=event.id,
        event_name=event.name,
        score=total,
        grade=grade,
        color=color,
        badge_css=badge_css,
        summary=summary,
        factors=factors,
        recommendations=recommendations,
    )
    cache.set(cache_key, result, timeout=60)
    return result


def generate_portfolio_briefing(events) -> str:

    """
    Generate a plain-English AI briefing for all active events.
    Uses OpenRouter if configured; falls back to deterministic summary.
    """
    from apps.ai_assistant.services import OpenRouterService

    scored = [compute_event_health(e) for e in events]

    # Always build a deterministic fallback briefing
    lines = []
    critical = [s for s in scored if s.score < 50]
    healthy = [s for s in scored if s.score >= 75]

    lines.append(f"Portfolio snapshot: {len(scored)} active event(s) analysed.")
    if healthy:
        lines.append(f"{len(healthy)} event(s) are healthy (score ≥75): {', '.join(s.event_name for s in healthy)}.")
    if critical:
        lines.append(f"⚠️  {len(critical)} event(s) need immediate attention: {', '.join(s.event_name for s in critical)}.")
        for s in critical:
            if s.recommendations:
                lines.append(f"  • {s.event_name}: {s.recommendations[0]}")

    all_recs = []
    for s in scored:
        all_recs.extend(s.recommendations)
    if all_recs:
        lines.append(f"Top priority action: {all_recs[0]}")

    fallback = " ".join(lines)

    if not OpenRouterService.is_configured():
        return fallback

    # Build enriched prompt for OpenRouter
    payload = [
        {
            "event": s.event_name,
            "health_score": s.score,
            "grade": s.grade,
            "factors": s.factors,
            "top_recommendations": s.recommendations[:3],
        }
        for s in scored
    ]
    messages = [
        {
            "role": "system",
            "content": (
                "You are an executive event operations briefing assistant. "
                "Given a portfolio health report, produce a concise morning briefing in 3-5 bullet points. "
                "Each bullet must be concrete and actionable. No headers. Plain text only."
            ),
        },
        {
            "role": "user",
            "content": f"Portfolio health data:\n{json.dumps(payload, indent=2)}\n\nGenerate today's executive briefing.",
        },
    ]
    try:
        return OpenRouterService._chat(messages, timeout=20)
    except Exception as exc:
        logger.warning("AI briefing generation failed: %s", exc)
        return fallback
