"""Built-in day plan templates."""

from __future__ import annotations

from typing import Dict, List

from .models import DayPlanBlock

DAY_PLANS: Dict[str, List[DayPlanBlock]] = {
    "maker_day": [
        DayPlanBlock(
            title="Daily Planning",
            start_time="09:00",
            duration_min=15,
            description="Review tasks and set priorities for the day.",
        ),
        DayPlanBlock(
            title="Deep Work Session",
            start_time="09:30",
            duration_min=120,
            description="Heads-down focus time on your most important project.",
        ),
        DayPlanBlock(
            title="Async Updates",
            start_time="12:00",
            duration_min=30,
            description="Send project updates and review responses.",
            add_google_meet=False,
        ),
        DayPlanBlock(
            title="Collaboration Block",
            start_time="13:30",
            duration_min=60,
            description="Schedule meetings or pair work requiring real-time collaboration.",
        ),
        DayPlanBlock(
            title="Shutdown Routine",
            start_time="16:30",
            duration_min=30,
            description="Wrap up, capture notes, and plan for tomorrow.",
        ),
    ],
    "manager_day": [
        DayPlanBlock(
            title="Team Standup",
            start_time="09:00",
            duration_min=30,
            description="Daily sync with the team to align on goals and blockers.",
            add_google_meet=True,
        ),
        DayPlanBlock(
            title="One-on-One Slot",
            start_time="10:00",
            duration_min=60,
            description="Reserve for coaching or skip-level chats.",
        ),
        DayPlanBlock(
            title="Focus Block",
            start_time="13:00",
            duration_min=90,
            description="Heads-down time for planning or strategic work.",
        ),
        DayPlanBlock(
            title="Stakeholder Check-ins",
            start_time="15:00",
            duration_min=60,
            description="Time boxed window for stakeholder conversations.",
            add_google_meet=True,
        ),
    ],
}


def list_plan_ids() -> List[str]:
    """Return the available built-in plan identifiers."""

    return sorted(DAY_PLANS.keys())


def get_plan(plan_id: str) -> List[DayPlanBlock]:
    """Return the blocks for the given plan identifier."""

    try:
        return DAY_PLANS[plan_id]
    except KeyError as exc:  # pragma: no cover - simple guard
        raise KeyError(f"Unknown day plan '{plan_id}'. Available: {', '.join(list_plan_ids())}") from exc
