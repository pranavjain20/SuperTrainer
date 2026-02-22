import uuid

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    db: AsyncSession,
    query: Select,
    model: type,
    sort_column,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
) -> tuple[list, bool]:
    """Apply cursor-based pagination to a query.

    Sorts by sort_column DESC with model.id ASC as tiebreaker.
    Returns (items, has_more).
    """
    query = query.order_by(sort_column.desc(), model.id)

    if cursor:
        cursor_row = await db.get(model, cursor)
        if cursor_row:
            cursor_value = getattr(cursor_row, sort_column.key)
            query = query.where(
                (sort_column < cursor_value)
                | ((sort_column == cursor_value) & (model.id > cursor_row.id))
            )

    result = await db.execute(query.limit(limit + 1))
    items = list(result.scalars().all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    return items, has_more
