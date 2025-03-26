import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from loguru import logger

from src.database.base_models.pydantic_manager import DataBaseManagerConfig
from src.database.models import WorkingWallets, WalletsTasks
from src.database.utils.db_manager import DataBaseUtils
from src.utils.data.helper import proxies
from config import *


async def clear_database(engine) -> None:
    async with AsyncSession(engine) as session:
        async with session.begin():
            for model in [WorkingWallets, WalletsTasks]:
                await session.execute(delete(model))
            await session.commit()
    logger.info("База данных очищена.")


async def generate_database(engine, private_keys: list[str], recipients: list[str]) -> None:
    await clear_database(engine)
    tasks = []

    if CLAIM:
        tasks.append('CLAIM')

    if TRANSFER:
        tasks.append('TRANSFER')

    proxy_index = 0
    for private_key in private_keys:
        with open('wallets.txt', 'r') as file:
            file_private_keys = [line.strip() for line in file]

        private_key_index = file_private_keys.index(private_key)
        recipient = None

        if TRANSFER:
            if len(private_keys) != len(recipients):
                logger.error(f'Количество кошельков не соответствует количеству адресов из recipients.txt')
                return
            recipient = recipients[private_key_index]

        proxy = proxies[proxy_index]
        proxy_index = (proxy_index + 1) % len(proxies)

        proxy_url = None
        change_link = ''
        if proxy:
            if MOBILE_PROXY:
                proxy_url, change_link = proxy.split('|')
            else:
                proxy_url = proxy

        db_utils = DataBaseUtils(
            manager_config=DataBaseManagerConfig(
                action='working_wallets'
            )
        )

        await db_utils.add_to_db(
            private_key=private_key,
            proxy=f'{proxy_url}|{change_link}' if MOBILE_PROXY else proxy_url,
            recipient=recipient,
            status='pending',
        )
        for task in tasks:
            db_utils = DataBaseUtils(
                manager_config=DataBaseManagerConfig(
                    action='wallets_tasks'
                )
            )
            await db_utils.add_to_db(
                private_key=private_key,
                status='pending',
                task_name=task
            )
