#!/usr/bin/env python3
"""
Add XP to a specific user.

Usage:
    python scripts/add_xp.py <user_id_or_email> <amount> [description]

Examples:
    python scripts/add_xp.py 1 500
    python scripts/add_xp.py user@example.com 1000 "Bonus de bienvenida"
    python scripts/add_xp.py 5 -200 "Ajuste manual"
"""
import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session
from app.models.user import User
from app.models.xp import XPTransaction, XPReason, level_from_xp


async def main(identifier: str, amount: int, description: str) -> None:
    async with async_session() as db:
        # Look up user by id or email
        if identifier.isdigit():
            user = await db.get(User, int(identifier))
        else:
            result = await db.execute(select(User).where(User.email == identifier))
            user = result.scalar_one_or_none()

        if not user:
            print(f"Error: usuario '{identifier}' no encontrado.")
            sys.exit(1)

        old_xp = user.total_xp
        old_level = user.level

        user.total_xp += amount
        user.monthly_xp += amount
        user.level = level_from_xp(user.total_xp)

        db.add(XPTransaction(
            user_id=user.id,
            amount=amount,
            reason=XPReason.MANUAL,
            description=description,
        ))

        await db.commit()

        sign = "+" if amount >= 0 else ""
        print(f"OK — {user.name} ({user.email})")
        print(f"  XP:    {old_xp:,} → {user.total_xp:,}  ({sign}{amount:,})")
        if user.level != old_level:
            print(f"  Nivel: {old_level} → {user.level}  🎉")
        else:
            print(f"  Nivel: {user.level}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    identifier = sys.argv[1]
    try:
        amount = int(sys.argv[2])
    except ValueError:
        print(f"Error: amount debe ser un entero (recibido: '{sys.argv[2]}')")
        sys.exit(1)

    description = sys.argv[3] if len(sys.argv) > 3 else "Ajuste manual de XP"

    asyncio.run(main(identifier, amount, description))
