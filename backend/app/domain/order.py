"""Доменные сущности заказа."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List
from dataclasses import dataclass, field

from .exceptions import (
    OrderAlreadyPaidError,
    OrderCancelledError,
    InvalidQuantityError,
    InvalidPriceError,
    InvalidAmountError,
)


# TODO: Реализовать OrderStatus (str, Enum)
# Значения: CREATED, PAID, CANCELLED, SHIPPED, COMPLETED
class OrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"
    COMPLETED = "completed"


# TODO: Реализовать OrderItem (dataclass)
# Поля: product_name, price, quantity, id, order_id
# Свойство: subtotal (price * quantity)
# Валидация: quantity > 0, price >= 0
@dataclass
class OrderItem:
    product_name: str
    price: Decimal
    quantity: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    order_id: uuid.UUID = None

    @property
    def subtotal(self) -> Decimal:
        return self.price * self.quantity 

    def __post_init__(self):
        if self.quantity <= 0:
            raise InvalidQuantityError(self.quantity)
        if self.price < 0:
            raise InvalidPriceError(self.price)


# TODO: Реализовать OrderStatusChange (dataclass)
# Поля: order_id, status, changed_at, id
@dataclass
class OrderStatusChange:
    order_id: uuid.UUID
    status: OrderStatus
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    changed_at: datetime = field(default_factory=datetime.utcnow)


# TODO: Реализовать Order (dataclass)
# Поля: user_id, id, status, total_amount, created_at, items, status_history
# Методы:
#   - add_item(product_name, price, quantity) -> OrderItem
#   - pay() -> None  [КРИТИЧНО: нельзя оплатить дважды!]
#   - cancel() -> None
#   - ship() -> None
#   - complete() -> None
@dataclass
class Order:
    user_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: OrderStatus = OrderStatus.CREATED
    total_amount: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.utcnow)
    items: List[OrderItem] = field(default_factory=list)
    status_history: List[OrderStatusChange] = field(default_factory=list)

    def add_item(self, product_name: str, price: Decimal, quantity: int) -> OrderItem:
        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError(self.id) 
        
        item = OrderItem(product_name=product_name, price=price, quantity=quantity, order_id=self.id)
        self.items.append(item)
        self._recalculate_total()
        return item

    def _recalculate_total(self):
        self.total_amount = sum((item.subtotal for item in self.items), Decimal("0"))

    def pay(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id)
        if self.status == OrderStatus.CANCELLED:
            raise OrderCancelledError(self.id)
        
        self.status = OrderStatus.PAID
        self._add_status_history(OrderStatus.PAID)

    def cancel(self) -> None:
        if self.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(self.id) 
        self.status = OrderStatus.CANCELLED
        self._add_status_history(OrderStatus.CANCELLED)

    def ship(self) -> None:
        if self.status != OrderStatus.PAID:
            raise ValueError("Заказ должен быть оплачен перед отправкой")
        self.status = OrderStatus.SHIPPED
        self._add_status_history(OrderStatus.SHIPPED)

    def complete(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise ValueError("Заказ должен быть отправлен перед завершением")
        self.status = OrderStatus.COMPLETED
        self._add_status_history(OrderStatus.COMPLETED)

    def _add_status_history(self, status: OrderStatus):
        self.status_history.append(OrderStatusChange(order_id=self.id, status=status))


