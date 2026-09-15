from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_session
from app.models.models import Admin, AuditLog, Tariff
from app.schemas import TariffIn, TariffOut

router = APIRouter(prefix="/api/tariffs", tags=["tariffs"])

@router.get("", response_model=list[TariffOut])
async def list_tariffs(
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("support")),
) -> list[TariffOut]:
    rows = await session.execute(select(Tariff).order_by(Tariff.sort_order, Tariff.id))
    return [TariffOut.model_validate(t) for t in rows.scalars().all()]

@router.post("", response_model=TariffOut)
async def create_tariff(
    data: TariffIn,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> TariffOut:
    tariff = Tariff(**data.model_dump())
    session.add(tariff)
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action="create",
            entity="tariff",
            details=data.name,
        )
    )
    await session.commit()
    await session.refresh(tariff)
    return TariffOut.model_validate(tariff)

@router.put("/{tariff_id}", response_model=TariffOut)
async def update_tariff(
    tariff_id: int,
    data: TariffIn,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> TariffOut:
    tariff = await session.get(Tariff, tariff_id)
    if tariff is None:
        raise HTTPException(404, "Тариф не найден")
    for key, value in data.model_dump().items():
        setattr(tariff, key, value)
    session.add(
        AuditLog(
            admin_id=admin.id,
            admin_name=admin.username,
            action="update",
            entity="tariff",
            details=data.name,
        )
    )
    await session.commit()
    await session.refresh(tariff)
    return TariffOut.model_validate(tariff)

@router.delete("/{tariff_id}")
async def delete_tariff(
    tariff_id: int,
    session: AsyncSession = Depends(get_session),
    admin: Admin = Depends(require_role("admin")),
) -> dict:
    tariff = await session.get(Tariff, tariff_id)
    if tariff is None:
        raise HTTPException(404, "Тариф не найден")
    await session.delete(tariff)
    await session.commit()
    return {"ok": True}
