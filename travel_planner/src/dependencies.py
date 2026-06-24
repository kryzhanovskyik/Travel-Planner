from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import models


async def get_project_or_404(project_id: int, owner_id: int, db: AsyncSession) -> models.Project:
    """Return the project owned by owner_id, or raise 404."""
    result = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.places).selectinload(models.Place.notes))
        .where(models.Project.id == project_id, models.Project.owner_id == owner_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def get_place_or_404(project_id: int, place_id: int, db: AsyncSession) -> models.Place:
    """Return the place belonging to project_id, or raise 404."""
    result = await db.execute(
        select(models.Place)
        .options(selectinload(models.Place.notes))
        .where(models.Place.id == place_id, models.Place.project_id == project_id)
    )
    place = result.scalar_one_or_none()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


async def get_note_or_404(place_id: int, note_id: int, db: AsyncSession) -> models.Note:
    """Return the note belonging to place_id, or raise 404."""
    result = await db.execute(
        select(models.Note).where(models.Note.id == note_id, models.Note.place_id == place_id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
