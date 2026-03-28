# Import all models so Alembic and SQLAlchemy can discover them
from app.models.division import Division, LeagueMembership, LeagueSeason
from app.models.exercise import Exercise, ExerciseType
from app.models.friendship import Friendship, FriendshipStatus
from app.models.gym import (
    BookingStatus,
    ClassBooking,
    ClassWaitlist,
    Gym,
    GymClassBlockType,
    GymClassLiveStatus,
    GymClassSchedule,
    GymClassTemplate,
    GymClassWorkout,
    GymClassWorkoutBlock,
    GymClassWorkoutExercise,
    GymLocation,
    GymMembership,
    GymSubscriptionPlan,
    GymTicketWallet,
    MembershipStatus,
    PlanType,
)
from app.models.record import PersonalRecord, RecordType
from app.models.session import SessionSet, SessionType, WorkoutSession
from app.models.template import TemplateBlock, WorkoutModality, WorkoutTemplate
from app.models.user import UnitsPreference, User, UserRole
from app.models.challenge import Challenge, ChallengeStatus
from app.models.message import CoachMessage
from app.models.product import GymProduct, ProductItemType, ProductRedemption
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
    "Gym",
    "GymLocation",
    "GymSubscriptionPlan",
    "GymMembership",
    "GymTicketWallet",
    "GymClassTemplate",
    "GymClassSchedule",
    "GymClassWorkout",
    "GymClassWorkoutBlock",
    "GymClassWorkoutExercise",
    "GymClassBlockType",
    "GymClassLiveStatus",
    "ClassBooking",
    "ClassWaitlist",
    "PlanType",
    "MembershipStatus",
    "BookingStatus",
    "SessionType",
    "GymProduct",
    "ProductItemType",
    "ProductRedemption",
    "CoachMessage",
    "Challenge",
    "ChallengeStatus",
]
