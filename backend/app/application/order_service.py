import uuid
from decimal import Decimal
from typing import List, Optional

from app.domain.order import Order, OrderItem, OrderStatus
from app.domain.exceptions import OrderNotFoundError, UserNotFoundError

class OrderService:
    """Сервис для операций с заказами."""

    def __init__(self, order_repo, user_repo):
        self.order_repo = order_repo
        self.user_repo = user_repo

    # TODO: Реализовать create_order(user_id) -> Order
    async def create_order(self, user_id: uuid.UUID) -> Order:
        # Проверяем, существует ли пользователь 
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id) 

        # Создаем новый доменный объект заказа 
        order = Order(user_id=user_id)

        # Сохраняем начальное состояние в репозиторий 
        await self.order_repo.save(order)
        return order

    # TODO: Реализовать get_order(order_id) -> Order
    async def get_order(self, order_id: uuid.UUID) -> Order:
        order = await self.order_repo.find_by_id(order_id) 
        if not order:
            raise OrderNotFoundError(order_id) 
        return order

    # TODO: Реализовать add_item(order_id, product_name, price, quantity) -> OrderItem
    async def add_item(
        self,
        order_id: uuid.UUID,
        product_name: str,
        price: Decimal,
        quantity: int,
    ) -> OrderItem:
        order = await self.get_order(order_id) 

        # Добавляем товар через доменный метод (там сработает валидация цены/количества) 
        item = order.add_item(product_name, price, quantity)

        # Persistence: сохраняем обновленный заказ с новым товаром и пересчитанной суммой 
        await self.order_repo.save(order)
        return item 

    # TODO: Реализовать pay_order(order_id) -> Order
    # КРИТИЧНО: гарантировать что нельзя оплатить дважды!
    async def pay_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id) 
        
        # Вызываем метод pay() доменного объекта. 
        # Если статус уже PAID, домен выбросит исключение OrderAlreadyPaidError.
        order.pay()

        # Сохраняем новый статус и запись в истории в БД 
        await self.order_repo.save(order)
        return order

    # TODO: Реализовать cancel_order(order_id) -> Order
    async def cancel_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id) 
        order.cancel() 
        await self.order_repo.save(order) 
        return order

    # TODO: Реализовать ship_order(order_id) -> Order
    async def ship_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id) 
        order.ship() 
        await self.order_repo.save(order) 
        return order

    # TODO: Реализовать complete_order(order_id) -> Order
    async def complete_order(self, order_id: uuid.UUID) -> Order:
        order = await self.get_order(order_id) 
        order.complete() 
        await self.order_repo.save(order) 
        return order

    # TODO: Реализовать list_orders(user_id: Optional) -> List[Order]
    async def list_orders(self, user_id: Optional[uuid.UUID] = None) -> List[Order]:
        if user_id:
            # Проверка пользователя перед фильтрацией 
            user = await self.user_repo.find_by_id(user_id)
            if not user:
                raise UserNotFoundError(user_id) 
            return await self.order_repo.find_by_user(user_id) 
        else:
            return await self.order_repo.find_all() 

    # TODO: Реализовать get_order_history(order_id) -> List[OrderStatusChange]
    async def get_order_history(self, order_id: uuid.UUID) -> List:
        order = await self.get_order(order_id) 
        return order.status_history 