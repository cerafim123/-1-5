from datetime import date, datetime, time, timedelta
from html import escape
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.api import get_current_user
from app.database import get_db
from app.models import Apartment, House, Master, Request, Resident, User

reports_router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Документы"],
)

def require_manager(user: User):
    if user.role not in {"dispatcher", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав для формирования документов",
        )

def get_house_or_404(db: Session, house_id: int) -> House:
    house = db.get(House, house_id)
    if house is None:
        raise HTTPException(status_code=404, detail="Дом не найден")
    return house

def request_rows(db: Session, conditions, include_due_at: bool = False):
    resident_user = aliased(User)
    master_user = aliased(User)

    columns = [
        Request.id,
        Request.created_at,
        Apartment.number.label("apartment_number"),
        House.address.label("house_address"),
        Request.request_type,
        Request.description,
        Request.priority,
        Request.status,
        resident_user.full_name.label("resident_name"),
        master_user.full_name.label("master_name"),
    ]

    if include_due_at:
        columns.append(Request.due_at)

    query = (
        select(*columns)
        .join(Apartment, Apartment.id == Request.apartment_id)
        .join(House, House.id == Apartment.house_id)
        .join(Resident, Resident.id == Request.resident_id)
        .join(resident_user, resident_user.id == Resident.user_id)
        .outerjoin(Master, Master.id == Request.master_id)
        .outerjoin(master_user, master_user.id == Master.user_id)
        .where(*conditions)
        .order_by(Request.created_at, Request.id)
    )

    return db.execute(query).all()

@reports_router.get(
    "/house-month.xlsx",
    summary="Скачать сводку по дому за месяц в XLSX",
    description=(
        "Формирует XLSX-файл по заявкам выбранного дома за календарный месяц. "
        "Файл содержит заголовок, дату формирования, таблицу и итоговое количество заявок."
    ),
    responses={
        200: {
            "description": "Сводка в формате XLSX",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
        },
        401: {"description": "Требуется авторизация"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Дом не найден"},
        422: {"description": "Некорректный месяц или год"},
    },
)
def download_house_month(
    house_id: int = Query(gt=0),
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_manager(user)
    house = get_house_or_404(db, house_id)

    start = datetime(year, month, 1)
    end = (
        datetime(year + 1, 1, 1)
        if month == 12
        else datetime(year, month + 1, 1)
    )

    rows = request_rows(
        db,
        [
            Apartment.house_id == house_id,
            Request.created_at >= start,
            Request.created_at < end,
        ],
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Сводка по дому"

    sheet.merge_cells("A1:J1")
    sheet["A1"] = f"Сводка по дому: {house.address}"
    sheet["A1"].font = Font(bold=True, size=16, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="1F4E78")
    sheet["A1"].alignment = Alignment(horizontal="center")

    sheet.merge_cells("A2:J2")
    sheet["A2"] = f"Период: {year}-{month:02d}"
    sheet["A2"].alignment = Alignment(horizontal="center")

    sheet.merge_cells("A3:J3")
    sheet["A3"] = f"Дата формирования: {datetime.now():%d.%m.%Y %H:%M}"
    sheet["A3"].alignment = Alignment(horizontal="center")

    headers = [
        "№ заявки",
        "Дата",
        "Дом",
        "Квартира",
        "Жилец",
        "Тип",
        "Описание",
        "Приоритет",
        "Статус",
        "Мастер",
    ]

    header_row = 5
    for column, value in enumerate(headers, start=1):
        cell = sheet.cell(row=header_row, column=column, value=value)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_index, row in enumerate(rows, start=header_row + 1):
        values = [
            row.id,
            row.created_at.strftime("%d.%m.%Y") if row.created_at else "",
            row.house_address or "",
            row.apartment_number or "",
            row.resident_name or "",
            row.request_type or "",
            row.description or "",
            row.priority or "",
            row.status or "",
            row.master_name or "",
        ]

        for column, value in enumerate(values, start=1):
            sheet.cell(row=row_index, column=column, value=value)
            sheet.cell(row=row_index, column=column).alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    total_row = header_row + len(rows) + 1
    sheet.merge_cells(
        start_row=total_row,
        start_column=1,
        end_row=total_row,
        end_column=9,
    )
    sheet.cell(row=total_row, column=1, value="Всего заявок за месяц:")
    sheet.cell(row=total_row, column=10, value=len(rows))
    sheet.cell(row=total_row, column=1).font = Font(bold=True)
    sheet.cell(row=total_row, column=10).font = Font(bold=True)

    widths = {
        "A": 12,
        "B": 13,
        "C": 25,
        "D": 12,
        "E": 22,
        "F": 18,
        "G": 42,
        "H": 14,
        "I": 16,
        "J": 22,
    }

    for column, width in widths.items():
        sheet.column_dimensions[column].width = width

    sheet.freeze_panes = "A6"
    sheet.auto_filter.ref = f"A{header_row}:J{header_row + len(rows)}"

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = f"house_{house_id}_{year}_{month:02d}.xlsx"

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

@reports_router.get(
    "/overdue.pdf",
    summary="Скачать отчёт о просроченных заявках в PDF",
    description=(
        "Формирует PDF-отчёт по незавершённым заявкам, срок исполнения которых истёк. "
        "Можно ограничить результат домом и периодом создания заявок."
    ),
    responses={
        200: {
            "description": "Отчёт в формате PDF",
            "content": {"application/pdf": {}},
        },
        401: {"description": "Требуется авторизация"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Дом не найден"},
        422: {"description": "Начало периода позже окончания"},
    },
)
def download_overdue_pdf(
    house_id: int | None = Query(default=None, gt=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_manager(user)

    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422,
            detail="Начало периода позже его окончания",
        )

    conditions = [
        Request.due_at.is_not(None),
        Request.due_at < datetime.now(),
        Request.status.not_in(("completed", "cancelled")),
    ]

    if house_id is not None:
        get_house_or_404(db, house_id)
        conditions.append(Apartment.house_id == house_id)

    if date_from:
        conditions.append(
            Request.created_at >= datetime.combine(date_from, time.min)
        )

    if date_to:
        conditions.append(
            Request.created_at
            < datetime.combine(date_to + timedelta(days=1), time.min)
        )

    rows = request_rows(db, conditions, include_due_at=True)

    font_path = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Arial.ttf"
    windows_font_path = Path("C:/Windows/Fonts/arial.ttf")

    if font_path.exists():
        selected_font = font_path
    elif windows_font_path.exists():
        selected_font = windows_font_path
    else:
        raise HTTPException(
            status_code=500,
            detail=(
                "Для PDF не найден Arial.ttf. Поместите файл шрифта "
                "в backend/app/assets/fonts/Arial.ttf"
            ),
        )

    pdfmetrics.registerFont(TTFont("ArialCyr", str(selected_font)))

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Отчёт о просроченных заявках",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CyrillicTitle",
        parent=styles["Title"],
        fontName="ArialCyr",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
    )
    normal_style = ParagraphStyle(
        "CyrillicNormal",
        parent=styles["Normal"],
        fontName="ArialCyr",
        fontSize=8,
        leading=10,
    )
    cell_style = ParagraphStyle(
        "CyrillicCell",
        parent=normal_style,
        fontSize=7,
        leading=8,
    )

    story = [
        Paragraph("Отчёт о просроченных заявках", title_style),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Дата формирования: {datetime.now():%d.%m.%Y %H:%M}",
            normal_style,
        ),
        Paragraph(
            f"Период создания: "
            f"{date_from.strftime('%d.%m.%Y') if date_from else 'не задан'} — "
            f"{date_to.strftime('%d.%m.%Y') if date_to else 'не задан'}",
            normal_style,
        ),
        Paragraph(
            f"Дом: {escape(str(house_id)) if house_id else 'все дома'}",
            normal_style,
        ),
        Paragraph(f"Всего просроченных заявок: {len(rows)}", normal_style),
        Spacer(1, 4 * mm),
    ]

    table_data = [[
        "№",
        "Дом",
        "Кв.",
        "Жилец",
        "Тип",
        "Описание",
        "Создана",
        "Срок",
        "Статус",
        "Мастер",
    ]]

    for row in rows:
        table_data.append([
            str(row.id),
            Paragraph(escape(row.house_address or ""), cell_style),
            escape(row.apartment_number or ""),
            Paragraph(escape(row.resident_name or ""), cell_style),
            Paragraph(escape(row.request_type or ""), cell_style),
            Paragraph(escape(row.description or ""), cell_style),
            row.created_at.strftime("%d.%m.%Y") if row.created_at else "",
            row.due_at.strftime("%d.%m.%Y") if row.due_at else "",
            escape(row.status or ""),
            Paragraph(escape(row.master_name or "Не назначен"), cell_style),
        ])

    table = LongTable(
        table_data,
        repeatRows=1,
        colWidths=[
            10 * mm,
            34 * mm,
            12 * mm,
            30 * mm,
            23 * mm,
            62 * mm,
            20 * mm,
            20 * mm,
            21 * mm,
            30 * mm,
        ],
    )
    table.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#EAF0F8"),
        ]),
    ]))

    story.append(table)
    document.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="overdue_requests.pdf"'
        },
    )
