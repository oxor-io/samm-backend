#!/usr/bin/env python3
import asyncio
import time

import conf
import db
import crud
import imap_client
from logger import logger


RECONNECT_DELAY = 30


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    if conf.INIT_DATABASE:
        loop.run_until_complete(db.init_db())
        # TODO: remove or refactor the fill_db_initial_txn function before release
        loop.run_until_complete(crud.fill_db_initial_txn(first_user_email='artem@oxor.io'))

    while True:
        try:
            loop.run_until_complete(imap_client.idle_loop())
        except:
            logger.exception(f'idle_loop is failed. reconnect after {RECONNECT_DELAY} sec')
            time.sleep(RECONNECT_DELAY)
