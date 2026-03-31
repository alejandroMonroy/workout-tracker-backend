from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.gym import BookingStatus, GymClassBlockType, GymClassLiveStatus, MembershipStatus, PlanType


# ── Gym ──────────────────────────────────────────────────────────────────────

class GymCreate(BaseModel):
    name: str
    description: str | None = None
    logo_url: str | None = None
    website: str | None = None
    phone: str | None = None
    free_trial_enabled: bool = True


class GymUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    logo_url: str | None = None
    website: str | None = None
    phone: str | None = None
    free_trial_enabled: bool | None = None


class GymPublic(BaseModel):
    id: int
    owner_id: int
    name: str
    description: str | None
    logo_url: str | None
    website: str | None
    phone: str | None
    free_trial_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Location ──────────────────────────────────────────────────────────────────

class LocationCreate(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    capacity: int = 20
    cancellation_hours: int = 2


class LocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    capacity: int | None = None
    cancellation_hours: int | None = None
    is_active: bool | None = None


class LocationPublic(BaseModel):
    id: int
    gym_id: int
    name: str
    address: str | None
    city: str | None
    capacity: int
    cancellation_hours: int
    is_active: bool

    model_config = {"from_attributes": True}


# ── Plan ──────────────────────────────────────────────────────────────────────

class PlanCreate(BaseModel):
    name: str
    plan_type: PlanType
    xp_price: int
    sessions_included: int | None = None
    ticket_count: int | None = None


class PlanUpdate(BaseModel):
    name: str | None = None
    xp_price: int | None = None
    sessions_included: int | None = None
    ticket_count: int | None = None
    is_active: bool | None = None


class PlanPublic(BaseModel):
    id: int
    location_id: int
    name: str
    plan_type: PlanType
    xp_price: int
    sessions_included: int | None
    ticket_count: int | None
    is_active: bool

    model_config = {"from_attributes": True}


# ── Membership ────────────────────────────────────────────────────────────────

class MembershipPublic(BaseModel):
    id: int
    gym_id: int
    user_id: int
    plan_id: int | None
    status: MembershipStatus
    tickets_remaining: int | None
    sessions_used_this_period: int
    started_at: datetime
    expires_at: datetime | None
    auto_renew: bool
    is_trial: bool
    gym_name: str | None = None
    plan_name: str | None = None
    plan_type: PlanType | None = None
    sessions_included: int | None = None

    model_config = {"from_attributes": True}


class MemberPublic(BaseModel):
    """Member as seen from gym dashboard."""
    membership_id: int
    user_id: int
    user_name: str
    user_email: str
    avatar_url: str | None
    plan_name: str | None
    status: MembershipStatus
    tickets_remaining: int | None
    sessions_used_this_period: int
    started_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class TicketPurchasePublic(BaseModel):
    purchased_at: datetime
    plan_name: str
    tickets_bought: int | None
    xp_spent: int


# ── Class template ────────────────────────────────────────────────────────────

class ClassTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    duration_minutes: int = 60
    max_capacity: int = 20
    tickets_cost: int = 1


class ClassTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    max_capacity: int | None = None
    tickets_cost: int | None = None


class ClassTemplatePublic(BaseModel):
    id: int
    location_id: int
    name: str
    description: str | None
    duration_minutes: int
    max_capacity: int
    tickets_cost: int

    model_config = {"from_attributes": True}


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    template_id: int
    location_id: int
    starts_at: datetime
    ends_at: datetime
    override_capacity: int | None = None


class ScheduleUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    override_capacity: int | None = None
    is_cancelled: bool | None = None
    workout_id: int | None = None


class SchedulePublic(BaseModel):
    id: int
    template_id: int
    location_id: int
    starts_at: datetime
    ends_at: datetime
    override_capacity: int | None
    is_cancelled: bool
    template_name: str | None = None
    location_name: str | None = None
    gym_name: str | None = None
    gym_id: int | None = None
    booked_count: int = 0
    effective_capacity: int = 0
    tickets_cost: int = 1
    user_booking_status: BookingStatus | None = None
    user_on_waitlist: bool = False
    user_waitlist_position: int | None = None
    waitlist_count: int = 0
    workout_id: int | None = None
    live_status: GymClassLiveStatus = GymClassLiveStatus.PENDING

    model_config = {"from_attributes": True}


# ── Booking ───────────────────────────────────────────────────────────────────

class BookingPublic(BaseModel):
    id: int
    schedule_id: int
    user_id: int
    status: BookingStatus
    tickets_used: int
    checked_in_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Analytics ─────────────────────────────────────────────────────────────────

class GymAnalytics(BaseModel):
    total_members: int
    active_members: int
    total_classes_this_month: int
    avg_attendance_rate: float
    revenue_xp_this_month: int


# ── Weekly slots ──────────────────────────────────────────────────────────────

class WeeklySlotCreate(BaseModel):
    day_of_week: int  # 0-6
    start_time: str   # "HH:MM"
    end_time: str     # "HH:MM"
    name: str
    capacity: int
    cost: int

class WeeklySlotPublic(BaseModel):
    id: int
    gym_id: int
    day_of_week: int
    start_time: str
    end_time: str
    name: str
    capacity: int
    cost: int

    model_config = ConfigDict(from_attributes=True)


class CopyDaySlotsBody(BaseModel):
    source_day: int  # 0-6
    target_day: int  # 0-6


# ── Gym Class Workout ──────────────────────────────────────────────────────────

class GymClassWorkoutExerciseCreate(BaseModel):
    exercise_id: int
    order: int = 0
    target_sets: int | None = None
    target_reps: int | None = None
    target_weight_kg: float | None = None
    target_distance_m: float | None = None
    target_duration_sec: int | None = None
    notes: str | None = None


class GymClassWorkoutExercisePublic(BaseModel):
    id: int
    block_id: int
    exercise_id: int
    exercise_name: str | None = None
    order: int
    target_sets: int | None
    target_reps: int | None
    target_weight_kg: float | None
    target_distance_m: float | None
    target_duration_sec: int | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class GymClassWorkoutBlockCreate(BaseModel):
    order: int = 0
    name: str
    block_type: GymClassBlockType
    duration_sec: int | None = None
    rounds: int | None = None
    work_sec: int | None = None
    rest_sec: int | None = None
    exercises: list[GymClassWorkoutExerciseCreate] = []


class GymClassWorkoutBlockPublic(BaseModel):
    id: int
    workout_id: int
    order: int
    name: str
    block_type: GymClassBlockType
    duration_sec: int | None
    rounds: int | None
    work_sec: int | None
    rest_sec: int | None
    exercises: list[GymClassWorkoutExercisePublic] = []

    model_config = ConfigDict(from_attributes=True)


class GymClassWorkoutCreate(BaseModel):
    name: str
    description: str | None = None
    blocks: list[GymClassWorkoutBlockCreate] = []


class GymClassWorkoutUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    blocks: list[GymClassWorkoutBlockCreate] | None = None


class GymClassWorkoutPublic(BaseModel):
    id: int
    gym_id: int
    name: str
    description: str | None
    created_at: datetime
    blocks: list[GymClassWorkoutBlockPublic] = []

    model_config = ConfigDict(from_attributes=True)


# ── Live class ─────────────────────────────────────────────────────────────────

class ClassLiveStatePublic(BaseModel):
    schedule_id: int
    live_status: GymClassLiveStatus
    live_block_index: int
    total_blocks: int
    elapsed_sec: int | None
    remaining_sec: int | None
    current_block: GymClassWorkoutBlockPublic | None
    workout_id: int | None
    workout_name: str | None


# ── Save class session ─────────────────────────────────────────────────────────

class ClassSessionSetCreate(BaseModel):
    exercise_id: int
    set_number: int
    sets_count: int | None = 1
    reps: int | None = None
    weight_kg: float | None = None
    distance_m: float | None = None
    duration_sec: int | None = None
    calories: float | None = None
    rpe: int | None = Field(None, ge=1, le=10)
    notes: str | None = None


class ClassSessionSaveRequest(BaseModel):
    sets: list[ClassSessionSetCreate] = []
    notes: str | None = None
    rpe: int | None = Field(None, ge=1, le=10)
    mood: str | None = None
    total_duration_sec: int | None = None
