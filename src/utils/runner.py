from typing import Optional

from loguru import logger

from src.utils.proxy_manager import Proxy
from src.claimer.walrus import Walrus
from src.utils.user.sui_account import SuiAccount


async def process_claim(mnemonic: str, proxy: Proxy | None) -> Optional[bool]:
    sui_ns = Walrus(
        mnemonic=mnemonic,
        proxy=proxy
    )
    logger.debug(sui_ns)
    claimed = await sui_ns.claim_tokens()
    if claimed:
        return True


async def process_transfer_tokens(mnemonic: str, recipient: str) -> Optional[bool]:
    account = SuiAccount(
        mnemonic=mnemonic,
    )
    transferred = await account.transfer_tokens(recipient)
    if transferred:
        return True
