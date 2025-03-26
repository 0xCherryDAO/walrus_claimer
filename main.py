from asyncio import run, set_event_loop_policy, gather, create_task, sleep
import random
import asyncio
from typing import Awaitable, Callable
import logging
import sys

from questionary import select, Choice

from config import PAUSE_BETWEEN_WALLETS, MOBILE_PROXY, ROTATE_IP, SHUFFLE_WALLETS, PAUSE_BETWEEN_MODULES
from src.database.generate_database import generate_database
from src.models.route import Route
from src.database.models import init_models, engine
from src.utils.manage_tasks import manage_tasks
from src.utils.retrieve_route import get_routes
from src.utils.runner import *

from src.utils.data.helper import private_keys, recipients

logging.getLogger("asyncio").setLevel(logging.CRITICAL)

if sys.platform == 'win32':
    set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def get_module():
    result = select(
        message="Выберете модуль",
        choices=[
            Choice(title="1) Сгенерировать новую базу данных с маршрутами", value=1),
            Choice(title="2) Отработать по базе данных", value=2),
        ],
        qmark="⚙️ ",
        pointer="✅ "
    ).ask()
    return result


async def process_task(routes: list[Route]) -> None:
    if not routes:
        logger.success(f'Все задания из базы данных выполнены')
        return

    tasks = []
    for route in routes:
        tasks.append(create_task(process_route(route)))

        time_to_pause = random.randint(PAUSE_BETWEEN_WALLETS[0], PAUSE_BETWEEN_WALLETS[1]) \
            if isinstance(PAUSE_BETWEEN_WALLETS, list) else PAUSE_BETWEEN_WALLETS
        logger.info(f'Sleeping {time_to_pause} seconds before next wallet...')
        await sleep(time_to_pause)

    await gather(*tasks)


async def process_route(route: Route) -> None:
    refueled = False
    if route.wallet.proxy:
        if route.wallet.proxy.proxy_url and MOBILE_PROXY and ROTATE_IP:
            await route.wallet.proxy.change_ip()

    private_key = route.wallet.private_key

    for task in route.tasks:
        if task == 'CLAIM':
            completed = await process_claim(private_key, proxy=route.wallet.proxy)
            if completed:
                await manage_tasks(private_key, task)

        if task == 'TRANSFER':
            completed = await process_transfer_tokens(private_key, recipient=route.wallet.recipient)
            if completed:
                await manage_tasks(private_key, task)

        time_to_pause = random.randint(PAUSE_BETWEEN_MODULES[0], PAUSE_BETWEEN_MODULES[1]) \
            if isinstance(PAUSE_BETWEEN_MODULES, list) else PAUSE_BETWEEN_MODULES

        logger.info(f'Sleeping {time_to_pause} seconds before next module...')
        await sleep(time_to_pause)


async def main(module: Callable) -> None:
    await init_models(engine)

    if module == 1:
        if SHUFFLE_WALLETS:
            random.shuffle(private_keys)
        logger.debug("Генерация новой базы данных с маршрутами...")
        await generate_database(engine, private_keys, recipients)
    elif module == 2:
        logger.debug("Отработка по базе данных...")
        routes = await get_routes(private_keys)
        await process_task(routes)
    else:
        print("Неверный выбор.")
        return


def start_event_loop(awaitable: Awaitable[None]) -> None:
    run(awaitable)


if __name__ == '__main__':
    module = get_module()
    start_event_loop(main(module))
