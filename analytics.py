from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.api import get_current_user
from app.database import get_db
from app.models import Apartment, House, Request, User

analytics_router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Аналитика"],
)

@analytics_router.get(
    "/dashboard",
    summary="Получить сводную аналитику по заявкам",
    description=(
        "Возвращает показатели, динамику заявок по месяцам, "
        "распределение по домам и типам. Все результаты учитывают выбранный период и дом."
    ),
)
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    house_id: int | None = Query(default=None, gt=0),
):
    if user.role not in {"dispatcher", "admin"}:
        raise HTTPException(status_code=403, detail="Недостаточно прав для просмотра аналитики")

    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="Начало периода позже его окончания")

    conditions = []

    if date_from:
        conditions.append(
            Request.created_at >= datetime.combine(date_from, time.min)
        )

    if date_to:
        conditions.append(
            Request.created_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )

    if house_id:
        conditions.append(Apartment.house_id == house_id)

    overdue_condition = (
        (Request.due_at.is_not(None))
        & (Request.due_at < datetime.now())
        & (~Request.status.in_(("completed", "cancelled")))
    )

    totals = db.execute(
        select(
            func.count(Request.id).label("total"),
            func.coalesce(
                func.sum(case((overdue_condition, 1), else_=0)),
                0,
            ).label("overdue"),
            func.coalesce(
                func.sum(case((Request.status == "completed", 1), else_=0)),
                0,
            ).label("completed"),
        )
        .join(Apartment, Apartment.id == Request.apartment_id)
        .where(*conditions)
    ).one()

    monthly_rows = db.execute(
        select(
            extract("year", Request.created_at).label("year"),
            extract("month", Request.created_at).label("month"),
            func.count(Request.id).label("count"),
        )
        .join(Apartment, Apartment.id == Request.apartment_id)
        .where(*conditions)
        .group_by(
            extract("year", Request.created_at),
            extract("month", Request.created_at),
        )
        .order_by(
            extract("year", Request.created_at),
            extract("month", Request.created_at),
        )
    ).all()

    house_rows = db.execute(
        select(
            House.id.label("house_id"),
            House.address.label("address"),
            func.count(Request.id).label("count"),
        )
        .join(Apartment, Apartment.house_id == House.id)
        .join(Request, Request.apartment_id == Apartment.id)
        .where(*conditions)
        .group_by(House.id, House.address)
        .order_by(func.count(Request.id).desc(), House.address)
    ).all()

    type_rows = db.execute(
        select(
            Request.request_type.label("type"),
            func.count(Request.id).label("count"),
        )
        .join(Apartment, Apartment.id == Request.apartment_id)
        .where(*conditions)
        .group_by(Request.request_type)
        .order_by(func.count(Request.id).desc(), Request.request_type)
    ).all()

    return {
        "filters": {
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "house_id": house_id,
        },
        "indicators": {
            "total_requests": totals.total or 0,
            "overdue_requests": int(totals.overdue or 0),
            "completed_requests":int(totals.completed or 0),
        },
        "monthly_requests": [
            {
                "month": f"{int(row.year):04d}-{int(row.month):02d}",
                "count": row.count,
            }
            for row in monthly_rows
        ],
        "requests_by_house": [
            {
                "house_id": row.house_id,
                "house": row.address,
                "count": row.count,
            }
            for row in house_rows
        ],
        "requests_by_type": [
            {
                "type": row.type,
                "count": row.count,
            }
            for row in type_rows
        ],
    }
