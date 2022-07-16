#! /usr/bin/env python3

import argparse
from argparse import RawTextHelpFormatter
import psycopg2
import telegram_helper
import sqlite3
import os

bot_token = open("bot_token.txt", "r").read()
db_file = "database.db"


def create_db():
    if not os.path.exists(db_file):
        with sqlite3.connect(db_file) as conn:
            conn.executescript(
                """
                         CREATE TABLE users(
                         user_id text primary key,
                         username text
                         ); 
                         """
            )
            conn.executescript(
                """
                        CREATE TABLE variables(
                        name text primary key,
                        value text
                        );
                         """
            )
            conn.executescript(
                """
                         insert into variables(name, value)
                         values
                         ('time', '1658001497030384546');
                         """
            )


def get_users():
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
                   select * from users
                   """
        )
        return cursor.fetchall()


def get_max_time():
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
                   select name, value from variables where name = 'time'
                   """
        )
        (text, value) = (cursor.fetchall())[0]
        return value


def update_max_time(new_max_time):
    with sqlite3.connect(db_file) as conn:
        conn.executescript(
            f"""
                       update variables
                       set value='{new_max_time}'
                       where name='time'
                       """
        )


def add_new_users():
    bot = telegram_helper.TelegramFacade(bot_token)
    updates = bot.get_updates()
    with sqlite3.connect(db_file) as conn:
        for update in updates:
            user_id = update.message.from_user.id
            username = update.message.from_user.username
            conn.executescript(
                f"""
                           insert or ignore into users(user_id, username)
                           values
                           ('{user_id}', '{username}');
                           """
            )


def get_new_transactions():
    cur_max_time = get_max_time()
    conn = psycopg2.connect(
        host="testnet.db.explorer.indexer.near.dev",
        database="testnet_explorer",
        user="public_readonly",
        password="nearprotocol",
    )
    cur = conn.cursor()
    cur.execute(
        f"""
              select 
                  block_timestamp as time,
                  signer_account_id as signer,
                  receiver_account_id as receiver,
                  transaction_hash as hash
              from 
                  transactions t
              where
                  receiver_account_id = 'nft.examples.testnet' and
                  block_timestamp > {cur_max_time}
              """
    )
    transactions = cur.fetchall()
    new_max_time = 0
    for (time, signer, receiver, hash) in transactions:
        new_max_time = max(new_max_time, time)
        print(signer, receiver, time)
        cur.execute(
            f"""
                select
                  transaction_hash as hash,
                  index_in_transaction as index,
                  action_kind as action,
                  args as args
                from 
                  transaction_actions t
                where
                  transaction_hash = '{hash}'
                """
        )
        for (hash, index, action, args) in cur.fetchall():
            if (
                "method_name" in args.keys()
                and args["method_name"] == "nft_mint"
                and "args_json" in args.keys()
                and "metadata" in args["args_json"].keys()
                and "token_id" in args["args_json"].keys()
                and "receiver_id" in args["args_json"].keys()
            ):
                print(index, action, args["args_json"]["metadata"])
                send_data_to_bot(
                    args["args_json"]["receiver_id"],
                    args["args_json"]["token_id"],
                    args["args_json"]["metadata"],
                )
    if new_max_time > int(cur_max_time):
        update_max_time(new_max_time)


def send_data_to_bot(receiver_id, token_id, metadata):
    bot = telegram_helper.TelegramFacade(bot_token)
    for (user_id, username) in get_users():
        bot.send_message(
            user_id,
            f"""
NFT MINTED
{receiver_id} received {metadata["copies"]} copies of '{token_id}' token, containing following metadata:
title: {metadata["title"]}
description: {metadata["description"]}
media: {metadata["media"]}
    """,
        )


if __name__ == "__main__":
    create_db()
    add_new_users()
    get_new_transactions()
