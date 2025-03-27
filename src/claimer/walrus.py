from asyncio import sleep
from typing import Optional

from loguru import logger

from pysui.sui.sui_txn.async_transaction import SuiTransactionAsync
from pysui.sui.sui_types import SuiString
from pysui import SuiAddress

from config import MOVE_CALL_PACKAGE, MOVE_CALL_FUNCTION, MOVE_CALL_MODULE
from src.utils.proxy_manager import Proxy
from src.utils.request_client.client import RequestClient
from src.utils.user.sui_account import SuiAccount


class Walrus(SuiAccount, RequestClient):
    def __init__(
            self,
            mnemonic: str,
            proxy: Proxy | None
    ):
        SuiAccount.__init__(self, mnemonic=mnemonic)
        RequestClient.__init__(self, proxy=proxy)

    def __str__(self) -> str:
        return f'[{self.wallet_address}] | Claiming tokens...'

    async def _get_nft_object_id(self) -> Optional[str]:
        objects = await self.client.get_objects(self.wallet_address, fetch_all=True)
        data = objects.result_data.to_dict()['data']

        for obj in data:
            try:
                if 'Walrus Airdrop' in obj['display']['data']['name']:
                    logger.success(f'{self.wallet_address} | Успешно нашел NFT на кошельке.')
                    return obj['objectId']
            except (KeyError, TypeError):
                continue
        logger.warning(f'[{self.wallet_address}] | Не удалось найти NFT на кошельке')

    async def claim_tokens(self) -> Optional[bool]:
        nft_object_id = await self._get_nft_object_id()
        if not nft_object_id:
            return None

        while True:
            try:
                nft_data = await self.client.get_object(nft_object_id)
                nft_object = nft_data.result_data
                locked_data = await self.client.get_object(nft_object.content.fields['locked_id'])
                locked_object = locked_data.result_data
                # print(nft_object)
                airdrop_config_data = await self.client.get_object(
                    '0x194ddb7dcc480aabc981d976c6327a7bb610de0d7aa6e2c29783cf9d59da7bb3'
                )
                tx = SuiTransactionAsync(client=self.client)
                clock_data = await self.client.get_object(
                    '0x0000000000000000000000000000000000000000000000000000000000000006'
                )

                unwrap_result = await tx.move_call(
                    target=SuiString(f"{MOVE_CALL_PACKAGE}::{MOVE_CALL_MODULE}::{MOVE_CALL_FUNCTION}"),
                    arguments=[
                        nft_object,
                        locked_object,
                        airdrop_config_data.result_data,
                        clock_data.result_data
                    ]
                )
                await tx.transfer_objects(
                    transfers=[unwrap_result],
                    recipient=self.wallet_address,
                )
                simulation_status = await self.simulate_tx(tx)
                if simulation_status is False:
                    continue

                status, digest = await self.send_tx(tx)
                if status is True:
                    logger.success(
                        f'[{self.wallet_address}] | Successfully claimed tokens '
                        f'| TX: https://suivision.xyz/txblock/{digest}'
                    )
                    return True
                logger.error(
                    f'[{self.wallet_address}] | Failed to claim tokens | TX: https://suivision.xyz/txblock/{digest}'
                )
                await sleep(0.1)
            except Exception as ex:
                print(ex)
                await sleep(0.1)
                continue
