"""Aggregate user tag lookups for autocomplete."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TagService:
    @staticmethod
    async def list_user_tags(db: AsyncSession, user_id: str) -> list[dict]:
        """Return distinct tags the user has used, ordered by most recent use.

        Uses SQLite's json_each to flatten the JSON array column.
        """
        result = await db.execute(
            text(
                """
                SELECT je.value AS tag, MAX(i.created_at) AS last_used_at
                FROM images AS i, json_each(i.tags) AS je
                WHERE i.user_id = :user_id
                GROUP BY je.value
                ORDER BY MAX(i.created_at) DESC
                """
            ),
            {"user_id": user_id},
        )
        rows = result.fetchall()
        return [{"tag": r[0], "last_used_at": r[1]} for r in rows]
