import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Client


async def list_clients(
    db: AsyncSession,
    trainer_id: uuid.UUID,
    *,
    cursor: uuid.UUID | None = None,
    limit: int = 20,
    include_archived: bool = False,
) -> tuple[list[Client], bool]:
    """Return (clients, has_more) for a trainer."""
    query = select(Client).where(Client.trainer_id == trainer_id)

    if not include_archived:
        query = query.where(Client.archived == False)  # noqa: E712

    query = query.order_by(Client.created_at.desc(), Client.id)

    if cursor:
        cursor_client = await db.get(Client, cursor)
        if cursor_client:
            query = query.where(
                (Client.created_at < cursor_client.created_at)
                | ((Client.created_at == cursor_client.created_at) & (Client.id > cursor_client.id))
            )

    result = await db.execute(query.limit(limit + 1))
    clients = list(result.scalars().all())

    has_more = len(clients) > limit
    if has_more:
        clients = clients[:limit]

    return clients, has_more


async def get_client(db: AsyncSession, client_id: uuid.UUID) -> Client | None:
    return await db.get(Client, client_id)


async def create_client(db: AsyncSession, trainer_id: uuid.UUID, **kwargs) -> Client:
    client = Client(trainer_id=trainer_id, **kwargs)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def update_client(db: AsyncSession, client: Client, **kwargs) -> Client:
    # NOTE: skips None values, so you can't clear optional fields via PATCH yet.
    # Acceptable for now — revisit when we need "set email to null" functionality.
    for key, value in kwargs.items():
        if value is not None:
            setattr(client, key, value)
    await db.commit()
    await db.refresh(client)
    return client


async def archive_client(db: AsyncSession, client: Client) -> Client:
    client.archived = True
    await db.commit()
    await db.refresh(client)
    return client
