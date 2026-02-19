"""Реализация репозиториев с использованием SQLAlchemy."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import User
from app.domain.order import Order, OrderItem, OrderStatus, OrderStatusChange


class UserRepository:
    """Репозиторий для User."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # TODO: Реализовать save(user: User) -> None
    # Используйте INSERT ... ON CONFLICT DO UPDATE
    async def save(self, user: User) -> None:
        """Сохраняет пользователя (создает нового или обновляет существующего)."""
        query = text("""
            INSERT INTO users (id, email, name, created_at)
            VALUES (:id, :email, :name, :created_at)
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name
        """)
        await self.session.execute(query, {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at
        })

    # TODO: Реализовать find_by_id(user_id: UUID) -> Optional[User]
    async def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        query = text("SELECT id, email, name, created_at FROM users WHERE id = :id")
        result = await self.session.execute(query, {"id": user_id})
        row = result.fetchone()
        if row:
            return User(id=row.id, email=row.email, name=row.name, created_at=row.created_at)
        return None
    
    # TODO: Реализовать find_by_email(email: str) -> Optional[User]
    async def find_by_email(self, email: str) -> Optional[User]:
        query = text("SELECT id, email, name, created_at FROM users WHERE email = :email")
        result = await self.session.execute(query, {"email": email})
        row = result.fetchone()
        if row:
            return User(id=row.id, email=row.email, name=row.name, created_at=row.created_at)
        return None
    
    # TODO: Реализовать find_all() -> List[User]
    async def find_all(self) -> List[User]:
        query = text("SELECT id, email, name, created_at FROM users")
        result = await self.session.execute(query)
        return [User(id=r.id, email=r.email, name=r.name, created_at=r.created_at) for r in result.fetchall()]

class OrderRepository:
    """Репозиторий для Order."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # TODO: Реализовать save(order: Order) -> None
    # Сохранить заказ, товары и историю статусов
    async def save(self, order: Order) -> None:
        """Сохраняет заказ, все его товары и историю статусов."""
        # 1. Сохраняем сам заказ
        await self.session.execute(text("""
            INSERT INTO orders (id, user_id, status, total_amount, created_at)
            VALUES (:id, :user_id, :status, :total_amount, :created_at)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                total_amount = EXCLUDED.total_amount
        """), {
            "id": order.id, "user_id": order.user_id, "status": order.status.value,
            "total_amount": order.total_amount, "created_at": order.created_at
        })

        # 2. Сохраняем товары (используем ON CONFLICT DO NOTHING, чтобы не дублировать)
        for item in order.items:
            await self.session.execute(text("""
                INSERT INTO order_items (id, order_id, product_name, price, quantity)
                VALUES (:id, :order_id, :product_name, :price, :quantity)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": item.id, "order_id": order.id, "product_name": item.product_name,
                "price": item.price, "quantity": item.quantity
            })

        # 3. Сохраняем новые записи в истории
        for history in order.status_history:
            await self.session.execute(text("""
                INSERT INTO order_status_history (id, order_id, status, changed_at)
                VALUES (:id, :order_id, :status, :changed_at)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": history.id, "order_id": order.id,
                "status": history.status.value, "changed_at": history.changed_at
            })

    # TODO: Реализовать find_by_id(order_id: UUID) -> Optional[Order]
    # Загрузить заказ со всеми товарами и историей
    # Используйте object.__new__(Order) чтобы избежать __post_init__
    async def find_by_id(self, order_id: uuid.UUID) -> Optional[Order]:
        """Загружает заказ со всеми вложенными данными."""
        # Загружаем основную инфу о заказе
        order_row = (await self.session.execute(
            text("SELECT * FROM orders WHERE id = :id"), {"id": order_id}
        )).fetchone()
        
        if not order_row:
            return None

        # Создаем объект Order в обход __post_init__, чтобы не срабатывали лишние валидации [cite: 55]
        order = object.__new__(Order)
        order.id = order_row.id
        order.user_id = order_row.user_id
        order.status = OrderStatus(order_row.status)
        order.total_amount = Decimal(str(order_row.total_amount))
        order.created_at = order_row.created_at
        order.items = []
        order.status_history = []

        # Загружаем товары
        items_rows = (await self.session.execute(
            text("SELECT * FROM order_items WHERE order_id = :id"), {"id": order_id}
        )).fetchall()
        for r in items_rows:
            item = OrderItem(product_name=r.product_name, price=Decimal(str(r.price)), quantity=r.quantity, id=r.id, order_id=r.order_id)
            order.items.append(item)

        # Загружаем историю
        history_rows = (await self.session.execute(
            text("SELECT * FROM order_status_history WHERE order_id = :id ORDER BY changed_at"), {"id": order_id}
        )).fetchall()
        for r in history_rows:
            change = OrderStatusChange(order_id=r.order_id, status=OrderStatus(r.status), id=r.id, changed_at=r.changed_at)
            order.status_history.append(change)

        return order
    
    # TODO: Реализовать find_by_user(user_id: UUID) -> List[Order]
    async def find_by_user(self, user_id: uuid.UUID) -> List[Order]:
        query = text("SELECT id FROM orders WHERE user_id = :user_id")
        result = await self.session.execute(query, {"user_id": user_id})
        orders = []
        for row in result.fetchall():
            order = await self.find_by_id(row.id)
            if order:
                orders.append(order)
        return orders
    
    # TODO: Реализовать find_all() -> List[Order]
    async def find_all(self) -> List[Order]:
        query = text("SELECT id FROM orders")
        result = await self.session.execute(query)
        orders = []
        for row in result.fetchall():
            order = await self.find_by_id(row.id)
            if order:
                orders.append(order)
        return orders