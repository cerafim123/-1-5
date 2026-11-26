from datetime import datetime, timedelta

from pwdlib import PasswordHash

from app.database import SessionLocal
from app.models import (
    Apartment,
    House,
    Master,
    Request,
    RequestStatusHistory,
    Resident,
    User,
)

password_hash = PasswordHash.recommended()
demo_password = "Demo12345!"

houses_data = [
    ("ул. Лесная, 12", 4),
    ("ул. Садовая, 3", 3),
    ("пр. Мира, 25", 5),
]

request_types = ["Сантехника", "Электрика", "Отопление", "Уборка", "Ремонт подъезда"]
statuses = ["new", "assigned", "in_progress", "completed", "cancelled"]
priorities = ["low", "normal", "high"]
descriptions = [
    "Протекает кран на кухне",
    "Не работает освещение в коридоре",
    "Холодная батарея в комнате",
    "Нужно убрать лестничную площадку",
    "Повреждена штукатурка у входа",
]

def main():
    with SessionLocal() as db:
        if db.query(House).first():
            print("В базе уже есть данные; начальное наполнение пропущено.")
            return

        houses = []
        apartments = []

        for address, entrances in houses_data:
            house = House(address=address, entrances_count=entrances)
            db.add(house)
            db.flush()
            houses.append(house)

            for number in range(1, 11):
                apartment = Apartment(
                    house_id=house.id,
                    number=str(number),
                    floor=((number - 1) % 5) + 1,
                    area=45 + number,
                )
                db.add(apartment)
                db.flush()
                apartments.append(apartment)

        dispatcher = User(
            full_name="Диспетчер УК",
            email="dispatcher@example.com",
            phone="+70000000001",
            password_hash=password_hash.hash(demo_password),
            role="dispatcher",
        )
        db.add(dispatcher)

        master_records = []
        for index, specialization in enumerate(
            ["Сантехника", "Электрика", "Обслуживание"], start=1
        ):
            user = User(
                full_name=f"Мастер {index}",
                email=f"master{index}@example.com",
                phone=f"+7000000000{index + 1}",
                password_hash=password_hash.hash(demo_password),
                role="master",
            )
            db.add(user)
            db.flush()

            master = Master(
                user_id=user.id,
                specialization=specialization,
                is_active=True,
            )
            db.add(master)
            db.flush()
            master_records.append(master)

        db.flush()

        for index, apartment in enumerate(apartments):
            resident_user = User(
                full_name=f"Жилец {index + 1}",
                email=f"resident{index + 1}@example.com",
                phone=f"+7999000{index:04d}",
                password_hash=password_hash.hash(demo_password),
                role="resident",
            )
            db.add(resident_user)
            db.flush()

            resident = Resident(
                user_id=resident_user.id,
                apartment_id=apartment.id,
            )
            db.add(resident)
            db.flush()

            status = statuses[index % len(statuses)]
            master = (
                master_records[index % len(master_records)]
                if status in {"assigned", "in_progress", "completed"}
                else None
            )
            created = datetime.now() - timedelta(days=index)

            request = Request(
                apartment_id=apartment.id,
                resident_id=resident.id,
                master_id=master.id if master else None,
                request_type=request_types[index % len(request_types)],
                description=descriptions[index % len(descriptions)],
                priority=priorities[index % len(priorities)],
                status=status,
                due_at=created + timedelta(days=5),
                completed_at=created + timedelta(days=2)
                if status == "completed"else None,
            )
            db.add(request)
            db.flush()

            db.add(
                RequestStatusHistory(
                    request_id=request.id,
                    changed_by_id=dispatcher.id,
                    old_status=None,
                    new_status=status,
                    comment="Заявка добавлена при начальном заполнении базы",
                )
            )

        db.commit()
        print("Добавлены тестовые данные: 3 дома и 30 заявок.")
        print("Демонстрационный пароль: Demo12345!")
        print("Учетная запись диспетчера: dispatcher@example.com")

if __name__ == "__main__":
    main()
