import json
import os
import time
import random

import ccxt

from loguru import logger
from ccxt import gate
from ccxt.base.types import Transaction

import config
import settings


def fetch_tx_fee(exchange, symbol: str = 'MEME', network='ERC20') -> float:
    data = exchange.fetch_transaction_fee(
        code=symbol,
        params={
            'network': network
        }
    )

    tx_fee = float(data[symbol]['withdraw']['ETH'])
    return tx_fee


def fetch_balance(exchange: gate, symbol: str = 'MEME') -> float:
    balance_list = exchange.fetch_balance()
    token_free_balance = balance_list[symbol]['free']

    return token_free_balance


def withdraw(exchange: gate, address: str, amount: float, symbol: str = 'MEME', network: str = 'ERC20') -> Transaction:
    tx = exchange.withdraw(
        code=symbol,
        amount=amount,
        address=address,
        params={
            'network': network
        }
    )

    return tx


def calc_withdrawal_amount(tx_fee: float) -> float:
    value = random.randrange(settings.DIST_MEME_RANGE[0], settings.DIST_MEME_RANGE[1])
    return value + tx_fee


def save_progress(account: str, status: bool = True) -> None:
    data = []
    file_path = 'data/wallet_progress.json'

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except json.JSONDecodeError:
            logger.warning('Problem reading wallet progress. Creating new wallet progress file.')
            data = []

    data.append({'account': account, 'status': status})

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def main():
    symbol = 'MEME'
    network = 'ERC20'

    exchange = ccxt.gate({
        'apiKey': config.API_KEY,
        'secret': config.API_SECRET,
    })

    with open('data/wallets.txt', 'r') as f:
        accounts = [line.strip() for line in f]

    logger.info(f"Total accounts: {len(accounts)}")

    if settings.SHUFFLE:
        logger.info("Shuffling wallets...")
        random.shuffle(accounts)

    for account in accounts:

        logger.info(f'Processing {account}')

        balance = fetch_balance(exchange=exchange, symbol=symbol)
        tx_fee = fetch_tx_fee(exchange=exchange, symbol=symbol, network=network)

        while tx_fee > settings.MAX_MEME_FEE_COST:
            logger.warning(f"Sleeping 10 secs"
                           f"\r\nTransaction fee is greater than: {settings.MAX_MEME_FEE_COST}"
                           f"\r\nCurrent tx fee: {tx_fee}"
                           f"\r\nTarget: {settings.MAX_MEME_FEE_COST}")

            tx_fee = fetch_tx_fee(exchange=exchange, symbol=symbol, network=network)
            time.sleep(10)

        amount = calc_withdrawal_amount(tx_fee=tx_fee)

        if amount > balance:
            logger.exception(f'Not enough funds for withdrawal transaction'
                             f'\r\nBalance: {balance} {symbol}'
                             f'\r\nAmount: {amount} {symbol}'
                             f'\r\nTransaction fee: {tx_fee} {symbol}')
            raise Exception()

        try:

            tx: Transaction = withdraw(
                exchange=exchange,
                address=account,
                amount=amount,
                symbol=symbol,
                network=network
            )

            total_cost = float(tx['info']['amount'])

            logger.info(f'Transaction successfully withdrawn for {account}'
                        f'\r\nTotal Cost: {total_cost} {symbol}'
                        f'\r\nTransaction fee: {tx_fee} {symbol}'
                        f'\r\nWill receive {total_cost - tx_fee} {symbol}')

            save_progress(account, True)

        except Exception as e:
            logger.error(f'Problem with withdrawal: {e}')
            save_progress(account, False)

        sleep_time = random.randrange(settings.SLEEP_RANGE[0], settings.SLEEP_RANGE[1])
        logger.info(f'Sleeping {sleep_time} secs...')
        time.sleep(sleep_time)

    logger.info("Done!")


if __name__ == '__main__':
    main()
