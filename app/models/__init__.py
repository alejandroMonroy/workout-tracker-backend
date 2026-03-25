# Import all models so Alembic and SQLAlchemy can discover them
from app.models.coach_subscription import CoachSubscription, CoachSubscriptionStatus
from app.models.division import Division, LeagueMembership, LeagueSeason
from app.models.event import Event, EventCollaborator, EventRegistration, EventStatus, RegistrationStatus
from app.models.exercise import Exercise, ExerciseType
from app.models.partner_company import PartnerCompany, Product
from app.models.plan import (
    BlockExercise,
    BlockType,
    Plan,
    PlanEnrollment,
    PlanEnrollmentStatus,
    PlanSession,
    SessionBlock,
)
from app.models.record import PersonalRecord, RecordType
from app.models.session import SessionSet, WorkoutSession
from app.models.template import TemplateBlock, WorkoutModality, WorkoutTemplate
from app.models.training_center import (
    CenterClass,
    CenterMemberRole,
    CenterMemberStatus,
    CenterMembership,
    CenterPlan,
    CenterSubscription,
    CenterSubscriptionStatus,
    ClassBooking,
    ClassBookingStatus,
    ClassStatus,
    TrainingCenter,
)
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
    "PlanEnrollment",
    "PlanEnrollmentStatus",
    "WorkoutSession",
    "SessionSet",
    "PersonalRecord",
    "RecordType",
    "CoachSubscription",
    "CoachSubscriptionStatus",
    "XPTransaction",
    "XPReason",
    "Division",
    "LeagueSeason",
    "LeagueMembership",
    "TrainingCenter",
    "CenterMembership",
    "CenterPlan",
    "CenterMemberRole",
    "CenterMemberStatus",
    "CenterSubscription",
    "CenterSubscriptionStatus",
    "CenterClass",
    "ClassStatus",
    "ClassBooking",
    "ClassBookingStatus",
    "PartnerCompany",
    "Product",
    "Event",
    "EventCollaborator",
    "EventRegistration",
    "EventStatus",
    "RegistrationStatus",
]
