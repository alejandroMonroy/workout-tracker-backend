# Import all models so Alembic and SQLAlchemy can discover them
from app.models.coach_athlete import CoachAthlete, CoachAthleteStatus
from app.models.division import Division, LeagueMembership, LeagueSeason
from app.models.exercise import Exercise, ExerciseType
from app.models.plan import (
    BlockExercise,
    BlockType,
    Plan,
    PlanSession,
    SessionBlock,
    Subscription,
    SubscriptionStatus,
)
from app.models.record import PersonalRecord, RecordType
from app.models.session import SessionSet, WorkoutSession
from app.models.template import TemplateBlock, WorkoutModality, WorkoutTemplate
from app.models.user import UnitsPreference, User, UserRole
from app.models.xp import XPReason, XPTransaction

__all__ = [
    "User",
    "UserRole",
    "UnitsPreference",
    "Exercise",
    "ExerciseType",
    "WorkoutTemplate",
    "TemplateBlock",
    "WorkoutModality",
    "Plan",
    "PlanSession",
    "SessionBlock",
    "BlockExercise",
    "BlockType",
    "Subscription",
    "SubscriptionStatus",
    "WorkoutSession",
    "SessionSet",
    "PersonalRecord",
    "RecordType",
    "CoachAthlete",
    "CoachAthleteStatus",
    "XPTransaction",
    "XPReason",
    "Division",
    "LeagueSeason",
    "LeagueMembership",
]
