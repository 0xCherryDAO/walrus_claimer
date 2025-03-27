import base64
from asyncio import sleep
from typing import Optional, Union

from loguru import logger

from pysui.abstracts import SignatureScheme
from pysui import SuiConfig, AsyncClient, SuiAddress, ObjectID
from pysui.sui.sui_txn.async_transaction import SuiTransactionAsync
from pysui.sui.sui_types import SuiTxBytes, SuiString
from pysui.sui.sui_builders.exec_builders import DryRunTransaction

from config import SUI_RPC, WAL_TOKEN_TYPE


class SuiAccount:
    def __init__(
            self,
            mnemonic: str,
            rpc: str = SUI_RPC
    ):
        self.config = SuiConfig.user_config(rpc_url=rpc)
        self.config.recover_keypair_and_address(
            scheme=SignatureScheme.ED25519,
            mnemonics=mnemonic,
            derivation_path="m/44'/784'/0'/0'/0'"
        )
        self.config.set_active_address(address=SuiAddress(self.config.addresses[0]))

        self.client = AsyncClient(self.config)
        self.wallet_address = self.client.config.active_address

    async def simulate_tx(self, tx: SuiTransactionAsync):
        tx_data = await tx.get_transaction_data()
        tx_b64 = base64.b64encode(tx_data.serialize()).decode()
        result = await self.client.execute(DryRunTransaction(tx_bytes=tx_b64))
        result_data = result.result_data
        if result_data.effects.status.status == 'success':
            return True
        logger.error(f'[{self.wallet_address}] | Claim simulation failed...')
        return False

    async def send_tx(self, tx: SuiTransactionAsync):
        tx_bytes = await tx.deferred_execution()
        sui_tx_bytes = SuiTxBytes(tx_bytes)
        sign_and_submit_res = await self.client.sign_and_submit(
            signer=self.config.active_address,
            tx_bytes=sui_tx_bytes
        )

        result_data = sign_and_submit_res.result_data
        status = True if result_data.effects.status.status == 'success' else False
        digest = result_data.digest
        return status, digest

    async def get_balance(self, coin_type: Union[SuiString, str]) -> tuple[int, str | None]:
        token = (
            await self.client.get_coin(
                coin_type=coin_type, address=self.config.active_address
            )
        ).result_data.to_dict()['data']
        if not token:
            return 0, None
        balance = int(token[0]['balance'])
        coin_object_id = token[0]['coinObjectId']
        return balance, coin_object_id

    async def transfer_tokens(self, recipient: str) -> Optional[bool]:
        logger.debug(f'[{self.wallet_address}] | Transferring to [{recipient}]')
        native_balance = await self.get_balance('0x2::sui::SUI')

        if native_balance == 0:
            logger.error(f'[{self.wallet_address}] | SUI balance is 0')
            return None

        wal_balance, coin_object_id = await self.get_balance(
            WAL_TOKEN_TYPE
        )
        if wal_balance == 0:
            logger.error(f'[{self.wallet_address}] | WAL balance is 0')
            return None

        tx = SuiTransactionAsync(client=self.client)

        await tx.transfer_sui(
            recipient=SuiAddress(recipient),
            from_coin=ObjectID(coin_object_id),
            amount=int(wal_balance)
        )
        status, digest = await self.send_tx(tx)
        if status is True:
            logger.success(
                f'[{self.wallet_address}] | Successfully transferred tokens '
                f'| TX: https://suivision.xyz/txblock/{digest}'
            )
            return True
