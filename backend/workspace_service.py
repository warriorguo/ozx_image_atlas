import json
import base64
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import Workspace, WorkspaceImage


async def save_workspace(
    session: AsyncSession,
    name: str,
    params: dict,
    export_filename: str,
    sprites: List[tuple],       # [(filename, bytes), ...]
    shadow_images: List[tuple],  # [(filename, bytes), ...]
    background: Optional[tuple], # (filename, bytes) or None
    workspace_id: Optional[str] = None,
    tile_backgrounds: Optional[List[tuple]] = None,  # [(filename, bytes), ...]
) -> dict:
    """Save or update a workspace."""
    now = datetime.utcnow()

    if workspace_id:
        # Update existing
        result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
        workspace = result.scalar_one_or_none()
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
        workspace.name = name
        workspace.params = json.dumps(params)
        workspace.export_filename = export_filename
        workspace.updated_at = now
        # Delete old images
        await session.execute(delete(WorkspaceImage).where(WorkspaceImage.workspace_id == workspace_id))
    else:
        workspace = Workspace(
            name=name,
            params=json.dumps(params),
            export_filename=export_filename,
            created_at=now,
            updated_at=now,
        )
        session.add(workspace)
        await session.flush()  # Get the ID

    # Save images
    order = 0
    for filename, data in sprites:
        session.add(WorkspaceImage(
            workspace_id=workspace.id,
            category="sprite",
            filename=filename,
            sort_order=order,
            data=data,
        ))
        order += 1

    order = 0
    for filename, data in shadow_images:
        session.add(WorkspaceImage(
            workspace_id=workspace.id,
            category="shadow",
            filename=filename,
            sort_order=order,
            data=data,
        ))
        order += 1

    if background:
        session.add(WorkspaceImage(
            workspace_id=workspace.id,
            category="background",
            filename=background[0],
            sort_order=0,
            data=background[1],
        ))

    if tile_backgrounds:
        for i, (filename, data) in enumerate(tile_backgrounds):
            session.add(WorkspaceImage(
                workspace_id=workspace.id,
                category="tile_background",
                filename=filename,
                sort_order=i,
                data=data,
            ))

    await session.commit()
    return {
        "id": workspace.id,
        "name": workspace.name,
        "export_filename": workspace.export_filename,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
    }


async def list_workspaces(session: AsyncSession) -> List[dict]:
    """List all workspaces (metadata only)."""
    result = await session.execute(
        select(Workspace).order_by(Workspace.updated_at.desc())
    )
    workspaces = result.scalars().all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "export_filename": w.export_filename,
            "created_at": w.created_at.isoformat(),
            "updated_at": w.updated_at.isoformat(),
        }
        for w in workspaces
    ]


async def load_workspace(session: AsyncSession, workspace_id: str) -> dict:
    """Load a workspace with all its data."""
    result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise ValueError(f"Workspace {workspace_id} not found")

    # Load images
    img_result = await session.execute(
        select(WorkspaceImage)
        .where(WorkspaceImage.workspace_id == workspace_id)
        .order_by(WorkspaceImage.sort_order)
    )
    images = img_result.scalars().all()

    sprites = []
    shadows = []
    background = None
    tile_backgrounds = []
    for img in images:
        entry = {
            "filename": img.filename,
            "data": base64.b64encode(img.data).decode("utf-8"),
        }
        if img.category == "sprite":
            sprites.append(entry)
        elif img.category == "shadow":
            shadows.append(entry)
        elif img.category == "background":
            background = entry
        elif img.category == "tile_background":
            tile_backgrounds.append(entry)

    return {
        "id": workspace.id,
        "name": workspace.name,
        "params": json.loads(workspace.params),
        "export_filename": workspace.export_filename,
        "sprites": sprites,
        "shadowImages": shadows,
        "background": background,
        "tileBackgrounds": tile_backgrounds,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
    }


async def delete_workspace(session: AsyncSession, workspace_id: str) -> bool:
    """Delete a workspace and its images."""
    result = await session.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        return False
    await session.execute(delete(WorkspaceImage).where(WorkspaceImage.workspace_id == workspace_id))
    await session.delete(workspace)
    await session.commit()
    return True
