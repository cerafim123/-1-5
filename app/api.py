import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Apartment,
    House,
    Master,
    Request,
    RequestStatusHistory,
    Resident,
    User,
)

load_dotenv()

router = APIRouter(prefix="/api/v1", tags=["Заявки"])
auth_router = APIRouter(prefix="/api/v1", tags=["Авторизация"])
directory_router = APIRouter(prefix="/api/v1", tags=["Справочники"])

password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("Добавьте JWT_SECRET_KEY в файл backend/.env")

JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60

STATUSES = ("new", "assigned", "in_progress", "completed", "cancelled")
PRIORITIES = ("low", "normal", "high")
MANAGER_ROLES = ("dispatcher", "admin")

class RegisterInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    apartment_id: int = Field(gt=0)

class LoginInput(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)

class TokenOutput(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CurrentUserOutput(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None
    role: str
    apartment_id: int | None
    house_address: str | None

class RequestCreate(BaseModel):
    request_type: str = Field(min_length=2, max_length=50)
    description: str = Field(min_length=10, max_length=2000)
    priority: Literal["low", "normal", "high"] = "normal"
    resident_id: int | None = Field(default=None, gt=0)

class RequestUpdate(BaseModel):
    request_type: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = Field(default=None, min_length=10, max_length=2000)
    priority: Literal["low", "normal", "high"] | None = None
    status: Literal[
        "new", "assigned", "in_progress", "completed", "cancelled"
    ] | None = None
    comment: str | None = Field(default=None, max_length=1000)
    master_id: int | None = Field(default=None, gt=0)

class RequestOutput(BaseModel):
    id: int
    apartment_id: int
    apartment_number: str | None
    house_address: str | None
    resident_id: int
    resident_name: str | None
    master_id: int | None
    master_name: str | None
    request_type: str
    description: str
    priority: str
    status: str
    created_at: datetime
    completed_at: datetime | None

class RequestListOutput(BaseModel):
    items: list[RequestOutput]
    total: int
    page: int
    page_size: int

class HistoryOutput(BaseModel):
    id: int
    request_id: int
    changed_by_id: int
    changed_by_name: str | None
    old_status: str | None
    new_status: str
    comment: str | None
    changed_at: datetime

class HouseOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    address: str
    entrances_count: int | None

class ApartmentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    house_id: int
    number: str
    floor: int | None

class MasterOutput(BaseModel):
    id: int
    user_id: int
    full_name: str
    specialization: str
    is_active: bool

def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user.id), "exp": expires},JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return user

def require_roles(*allowed_roles: str):
    def check_role(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    return check_role

def get_resident_of(user: User, db: Session) -> Resident | None:
    return db.scalar(select(Resident).where(Resident.user_id == user.id))

def get_master_of(user: User, db: Session) -> Master | None:
    return db.scalar(select(Master).where(Master.user_id == user.id))

def request_to_output(request: Request) -> RequestOutput:
    apartment = request.apartment
    house = apartment.house if apartment else None
    resident = request.resident
    resident_user = resident.user if resident else None
    master = request.master
    master_user = master.user if master else None

    return RequestOutput(
        id=request.id,
        apartment_id=request.apartment_id,
        apartment_number=apartment.number if apartment else None,
        house_address=house.address if house else None,
        resident_id=request.resident_id,
        resident_name=resident_user.full_name if resident_user else None,
        master_id=request.master_id,
        master_name=master_user.full_name if master_user else None,
        request_type=request.request_type,
        description=request.description,
        priority=request.priority,
        status=request.status,
        created_at=request.created_at,
        completed_at=request.completed_at,
    )

def get_accessible_request(request_id: int, user: User, db: Session) -> Request:
    request = db.get(Request, request_id)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена",
        )

    if user.role == "resident":
        resident = get_resident_of(user, db)
        if resident is None or request.resident_id != resident.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к этой заявке",
            )
    elif user.role == "master":
        master = get_master_of(user, db)
        if master is None or request.master_id != master.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Заявка вам не назначена",
            )
    elif user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    return request

@auth_router.post(
    "/auth/register",
    response_model=TokenOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Зарегистрировать жильца",
    response_description="Токен доступа для созданной учетной записи",
    responses={
        404:{"description": "Квартира не найдена"},
        409: {"description": "Электронная почта уже зарегистрирована"},
        422: {"description": "Данные не прошли проверку"},
    },
)
def register(
    data: RegisterInput,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    email = data.email.strip().lower()

    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Эта электронная почта уже зарегистрирована",
        )

    apartment = db.get(Apartment, data.apartment_id)
    if apartment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Квартира не найдена",
        )

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        phone=data.phone,
        password_hash=password_hasher.hash(data.password),
        role="resident",
    )

    try:
        db.add(user)
        db.flush()
        db.add(Resident(user_id=user.id, apartment_id=apartment.id))
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Не удалось создать учетную запись",
        ) from error

    response.headers["Location"] = "/api/v1/auth/me"
    return TokenOutput(access_token=create_access_token(user))

@auth_router.post(
    "/auth/login",
    response_model=TokenOutput,
    summary="Войти в систему",
    responses={401: {"description": "Неверная почта или пароль"}},
)
def login(
    data: LoginInput,
    db: Annotated[Session, Depends(get_db)],
):
    email = data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is None or not password_hasher.verify(
        data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная электронная почта или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenOutput(access_token=create_access_token(user))

@auth_router.get(
    "/auth/me",
    response_model=CurrentUserOutput,
    summary="Получить текущего пользователя",
    responses={401: {"description": "Требуется авторизация"}},
)
def get_me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    apartment = None
    house = None

    if user.role == "resident":
        resident = get_resident_of(user, db)
        if resident is not None:
            apartment = resident.apartment
            house = apartment.house if apartment else None

    return CurrentUserOutput(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        apartment_id=apartment.id if apartment else None,
        house_address=house.address if house else None,
    )

@router.get(
    "/requests",
    response_model=RequestListOutput,
    summary="Получить список заявок",
    description=(
        "Возвращает заявки, доступные роли пользователя. Поддерживает фильтрацию "
        "по статусу, типу и дому, поиск по описанию, сортировку и постраничный вывод."
    ),
    responses={
        401: {"description": "Требуется авторизация"},
        403: {"description": "Недостаточно прав"},
    },
)
def list_requests(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    request_type: str | None = Query(default=None, max_length=50),
    house_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=100),
    sort_by: Literal["created_at", "priority", "status"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
):
    conditions = []

    if user.role == "resident":
        resident =get_resident_of(user, db)
        if resident is None:
            return RequestListOutput(
                items=[], total=0, page=page, page_size=page_size
            )
        conditions.append(Request.resident_id == resident.id)
    elif user.role == "master":
        master = get_master_of(user, db)
        if master is None:
            return RequestListOutput(
                items=[], total=0, page=page, page_size=page_size
            )
        conditions.append(Request.master_id == master.id)
    elif user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    if status_filter:
        conditions.append(Request.status == status_filter)

    if request_type:
        conditions.append(Request.request_type == request_type)

    if house_id:
        conditions.append(Request.apartment.has(Apartment.house_id == house_id))

    if search:
        term = f"%{search.strip()}%"
        conditions.append(
            or_(
                Request.description.like(term),
                Request.request_type.like(term),
            )
        )

    query = select(Request).where(*conditions)
    count_query = select(func.count(Request.id)).where(*conditions)

    sort_column = getattr(Request, sort_by)
    query = query.order_by(
        sort_column.asc() if sort_order == "asc" else sort_column.desc()
    )

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.offset((page - 1) * page_size).limit(page_size)
    ).all()

    return RequestListOutput(
        items=[request_to_output(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.post(
    "/requests",
    response_model=RequestOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Создать заявку",
    responses={
        401: {"description": "Требуется авторизация"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Жилец не найден"},
        422: {"description": "Данные не прошли проверку"},
    },
)
def create_request(
    data: RequestCreate,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_roles("resident", *MANAGER_ROLES))
    ],
):
    if user.role == "resident":
        resident = get_resident_of(user, db)
        if resident is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учетная запись не связана с квартирой",
            )
    else:
        if data.resident_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Укажите resident_id жильца, от имени которого создается заявка",
            )
        resident = db.get(Resident, data.resident_id)
        if resident is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Жилец не найден",
            )

    request = Request(
        apartment_id=resident.apartment_id,
        resident_id=resident.id,
        request_type=data.request_type.strip(),
        description=data.description.strip(),
        priority=data.priority,
        status="new",
    )

    try:
        db.add(request)
        db.flush()
        db.add(
            RequestStatusHistory(
                request_id=request.id,
                changed_by_id=user.id,
                old_status=None,
                new_status="new",
                comment="Заявка создана",
            )
        )
        db.commit()
        db.refresh(request)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Данные заявки не прошли проверку",
        ) from error

    response.headers["Location"] = f"/api/v1/requests/{request.id}"
    return request_to_output(request)

@router.get(
    "/requests/{request_id}",response_model=RequestOutput,
    summary="Получить заявку",
    responses={
        401: {"description": "Требуется авторизация"},
        403: {"description": "Заявка недоступна пользователю"},
        404: {"description": "Заявка не найдена"},
    },
)
def get_request(
    request_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    return request_to_output(get_accessible_request(request_id, user, db))

@router.patch(
    "/requests/{request_id}",
    response_model=RequestOutput,
    summary="Изменить заявку",
    description=(
        "Жилец изменяет описание и приоритет своей новой заявки. Мастер меняет "
        "статус назначенной ему заявки. Диспетчер и администратор изменяют любые "
        "поля и назначают мастера через master_id."
    ),
    responses={
        401: {"description": "Требуется авторизация"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Заявка или мастер не найдены"},
        422: {"description": "Данные не прошли проверку"},
    },
)
def update_request(
    request_id: int,
    data: RequestUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    request = get_accessible_request(request_id, user, db)
    changes = data.model_dump(exclude_unset=True)
    comment = changes.pop("comment", None)
    old_status = request.status
    new_status = old_status

    if user.role == "resident":
        if request.status != "new" or request.master_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Изменять можно только новую неназначенную заявку",
            )
        if set(changes) - {"request_type", "description", "priority"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Жилец может изменить только тип, описание и приоритет",
            )
    elif user.role == "master":
        if set(changes) - {"status"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Мастер может изменить только статус заявки",
            )
        if "status" not in changes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Укажите новый статус заявки",
            )
    elif user.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    if "master_id" in changes:
        master_id = changes.pop("master_id")
        if master_id is None:
            request.master_id = None
            if request.status == "assigned":
                new_status = "new"
        else:
            master = db.get(Master, master_id)
            if master is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Мастер не найден",
                )
            if not master.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Мастер недоступен для назначения",
                )
            request.master_id = master.id
            if request.status == "new":
                new_status = "assigned"

    for field in ("request_type", "description", "priority"):
        if changes.get(field) is not None:
            setattr(request, field, changes[field])

    if changes.get("status") is not None:
        new_status = changes["status"]

    if new_status != old_status:
        request.status = new_status

        if new_status == "completed":
            request.completed_at = datetime.now()
        else:
            request.completed_at = None

        db.add(
            RequestStatusHistory(
                request_id=request.id,
                changed_by_id=user.id,
                old_status=old_status,
                new_status=new_status,comment=comment,
            )
        )

    try:
        db.commit()
        db.refresh(request)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Не удалось сохранить изменения",
        ) from error

    return request_to_output(request)

@router.delete(
    "/requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить заявку",
    responses={
        401: {"description": "Требуется авторизация"},
        403: {"description": "Недостаточно прав"},
        404: {"description": "Заявка не найдена"},
    },
)
def delete_request(
    request_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    request = get_accessible_request(request_id, user, db)

    if user.role == "master":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Мастер не может удалять заявки",
        )

    if user.role == "resident" and (
        request.status != "new" or request.master_id is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удалить можно только новую неназначенную заявку",
        )

    db.delete(request)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get(
    "/requests/{request_id}/history",
    response_model=list[HistoryOutput],
    summary="Получить историю статусов заявки",
    responses={
        401: {"description": "Требуется авторизация"},
        403: {"description": "Заявка недоступна пользователю"},
        404: {"description": "Заявка не найдена"},
    },
)
def get_request_history(
    request_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    get_accessible_request(request_id, user, db)

    entries = db.scalars(
        select(RequestStatusHistory)
        .where(RequestStatusHistory.request_id == request_id)
        .order_by(RequestStatusHistory.changed_at)
    ).all()

    author_ids = {entry.changed_by_id for entry in entries}
    authors = {}

    if author_ids:
        for author in db.scalars(
            select(User).where(User.id.in_(author_ids))
        ).all():
            authors[author.id] = author.full_name

    return [
        HistoryOutput(
            id=entry.id,
            request_id=entry.request_id,
            changed_by_id=entry.changed_by_id,
            changed_by_name=authors.get(entry.changed_by_id),
            old_status=entry.old_status,
            new_status=entry.new_status,
            comment=entry.comment,
            changed_at=entry.changed_at,
        )
        for entry in entries
    ]

@directory_router.get(
    "/houses",
    response_model=list[HouseOutput],
    summary="Получить список домов",
    responses={401: {"description": "Требуется авторизация"}},
)
def list_houses(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    return db.scalars(select(House).order_by(House.address)).all()

@directory_router.get(
    "/apartments",
    response_model=list[ApartmentOutput],
    summary="Получить список квартир",
    responses={401: {"description": "Требуется авторизация"}},
)
def list_apartments(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    house_id: int | None = Query(default=None, gt=0),
):
    query = select(Apartment).order_by(Apartment.house_id, Apartment.number)

    if house_id:
        query = query.where(Apartment.house_id == house_id)

    return db.scalars(query).all()

@directory_router.get(
    "/masters",
    response_model=list[MasterOutput],
    summary="Получить список мастеров",
    responses={401: {"description": "Требуется авторизация"}},
)
def list_masters(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    only_active: bool = Query(default=False),
):
    query = (select(Master)
        .join(User, User.id == Master.user_id)
        .order_by(User.full_name)
    )

    if only_active:
        query = query.where(Master.is_active.is_(True))

    masters = db.scalars(query).all()

    return [
        MasterOutput(
            id=master.id,
            user_id=master.user_id,
            full_name=master.user.full_name,
            specialization=master.specialization,
            is_active=master.is_active,
        )
        for master in masters
    ]
