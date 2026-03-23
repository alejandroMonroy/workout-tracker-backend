"""add training centers, companies, events

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-03-25 10:00:00.000000+00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Training Centers ──
    op.create_table(
        "training_centers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Center Memberships ──
    center_member_role = sa.Enum(
        "member", "coach", "admin", name="centermemberrole"
    )
    center_member_status = sa.Enum(
        "pending", "active", "rejected", "cancelled", name="centermemberstatus"
    )

    op.create_table(
        "center_memberships",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "center_id",
            sa.Integer,
            sa.ForeignKey("training_centers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True
        ),
        sa.Column("role", center_member_role, nullable=False, server_default="member"),
        sa.Column(
            "status", center_member_status, nullable=False, server_default="pending"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Center Plans ──
    op.create_table(
        "center_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "center_id",
            sa.Integer,
            sa.ForeignKey("training_centers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "plan_id",
            sa.Integer,
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Partner Companies ──
    op.create_table(
        "partner_companies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Products ──
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("partner_companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price", sa.Float, nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("external_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Events ──
    event_status = sa.Enum(
        "draft", "published", "cancelled", "completed", name="eventstatus"
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("capacity", sa.Integer, nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("status", event_status, nullable=False, server_default="draft"),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "center_id",
            sa.Integer,
            sa.ForeignKey("training_centers.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("partner_companies.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Event Collaborators ──
    op.create_table(
        "event_collaborators",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer,
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("partner_companies.id"),
            nullable=True,
        ),
        sa.Column(
            "center_id",
            sa.Integer,
            sa.ForeignKey("training_centers.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Event Registrations ──
    registration_status = sa.Enum(
        "registered", "cancelled", "attended", name="registrationstatus"
    )

    op.create_table(
        "event_registrations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer,
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True
        ),
        sa.Column(
            "status",
            registration_status,
            nullable=False,
            server_default="registered",
        ),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("event_registrations")
    op.drop_table("event_collaborators")
    op.drop_table("events")
    op.drop_table("products")
    op.drop_table("partner_companies")
    op.drop_table("center_plans")
    op.drop_table("center_memberships")
    op.drop_table("training_centers")

    sa.Enum(name="registrationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="eventstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="centermemberstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="centermemberrole").drop(op.get_bind(), checkfirst=True)
