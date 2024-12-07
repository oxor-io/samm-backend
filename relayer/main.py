#!/usr/bin/env python3
import asyncio

import conf
import db
import crud
import imap_client


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init_db())
    # TODO: remove or refactor the fill_db_initial_tx function before release
    loop.run_until_complete(crud.fill_db_initial_tx(first_user_email='artem@oxor.io'))
    loop.run_until_complete(imap_client.idle_loop())
