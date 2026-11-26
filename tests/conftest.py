import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import password_hasher
from app.database import Base, get_db
from app.main import app
from app.models import (
    Apartment,
    House,
    Master,
    Request as ServiceRequest,
    Resident,
    User,
)

TEST_PASSWORD = "TestPass123!"

@pytest.fixture
def test_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        house = House(address="Тестовая улица, 1", entrances_count=2)
        db.add(house)
        db.flush()

        apartment1 = Apartment(
            house_id=house.id,
            number="1",
            floor=1,
        )
        apartment2 = Apartment(
            house_id=house.id,
            number="2",
            floor=1,
        )
        db.add_all([apartment1, apartment2])
        db.flush()

        resident_user1 = User(
            full_name="Тестовый Жилец Один",
            email="resident1@test.local",
            phone="+70000000001",
            password_hash=password_hasher.hash(TEST_PASSWORD),
            role="resident",
        )
        resident_user2 = User(
            full_name="Тестовый Жилец Два",
            email="resident2@test.local",
            phone="+70000000002",
            password_hash=password_hasher.hash(TEST_PASSWORD),
            role="resident",
        )
        dispatcher_user = User(
            full_name="Тестовый Диспетчер",
            email="dispatcher@test.local",
            phone="+70000000003",
            password_hash=password_hasher.hash(TEST_PASSWORD),
            role="dispatcher",
        )
        master_user = User(
            full_name="Тестовый Мастер",
            email="master@test.local",
            phone="+70000000004",
            password_hash=password_hasher.hash(TEST_PASSWORD),
            role="master",
        )

        db.add_all([
            resident_user1,
            resident_user2,
            dispatcher_user,
            master_user,
        ])
        db.flush()

        resident1 = Resident(
            user_id=resident_user1.id,
            apartment_id=apartment1.id,
        )
        resident2 = Resident(
            user_id=resident_user2.id,
            apartment_id=apartment2.id,
        )
        master = Master(
            user_id=master_user.id,
            specialization="Сантехника",
            is_active=True,
        )

        db.add_all([resident1, resident2, master])
        db.flush()

        request1 = ServiceRequest(
            apartment_id=apartment1.id,
            resident_id=resident1.id,
            request_type="Сантехника",
            description="Протекает кран в ванной комнате",
            priority="normal",
            status="new",
        )
        request2 = ServiceRequest(
            apartment_id=apartment2.id,
            resident_id=resident2.id,
            request_type="Электрика",
            description="Не работает освещение в коридоре",
            priority="high",
            status="new",
        )
        request3 = ServiceRequest(
            apartment_id=apartment1.id,
            resident_id=resident1.id,
            master_id=master.id,
            request_type="Сантехника",
            description="Требуется проверить трубы отопления",
            priority="normal",
            status="assigned",
        )

        db.add_all([request1, request2, request3])
        db.commit()

        ids = {
            "house": house.id,
            "apartment1": apartment1.id,
            "resident1": resident1.id,
            "resident2": resident2.id,
            "master": master.id,
            "request1": request1.id,
            "request2": request2.id,"request3": request3.id,
        }

    def override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, TestingSessionLocal, ids
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
