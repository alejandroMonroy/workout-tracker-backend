# Import all models so Alembic and SQLAlchemy can discover them
from app.models.division import Division, LeagueMembership, LeagueSeason
from app.models.exercise import Exercise, ExerciseType
from app.models.friendship import Friendship, FriendshipStatus
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
    "WorkoutSession",
    "SessionSet",
    "PersonalRecord",
    "RecordType",
    "XPTransaction",
    "XPReason",
    "Division",
    "LeagueSeason",
    "LeagueMembership",
    "Friendship",
    "FriendshipStatus",
]
