#!/usr/bin/python3

#
# Atomize ep_newshub_rss database entries.
#
# Information is stored in normalized form in database eptwitter. The eptwitter db is created
# in advance using the script eptwitter/db/create_database.sql. User atomizer is created by script
# eptwitter/db/create_user.sql.
# The mysql.connector returns db entries as tuples. A row of the table ep_newshub_rss.item
# follows the form
#   (
#    id,                    # 0
#    published,             # 1
#    updated,               # 2
#    title,                 # 3
#    link,                  # 4
#    summary,               # 5
#    item_id,               # 6
#    feedsource,            # 7
#    summary_translation,   # 8
#    original_language      # 9
#   )
# .
#

import json
import re
import mysql.connector
import pprint

ep_newshub_rss_config = {
    'user': 'atomizer',
    'password': 'atomizer_password',
    'host': '127.0.0.1',
    'database': 'ep_newshub_rss',
    'charset': 'utf8mb4',
    'raise_on_warnings': True
}

eptwitter_config = {
    'user': 'atomizer',
    'password': 'atomizer_password',
    'host': '127.0.0.1',
    'database': 'eptwitter',
    'charset': 'utf8mb4',
    'raise_on_warnings': True
}

def load_batch_from_db(start_id, batch_size, cursor):
    cursor.execute("SELECT * FROM items WHERE id >= %s AND id < %s;", (start_id, (start_id + batch_size)))
    return cursor.fetchall()

def get_id(tweet):
    return tweet[0]
    
def get_published(tweet):
    # return tweet[1]
    return "2019-03-01 17:43:12"

def get_author(tweet):
    return tweet[3].split(':')[0]

def get_body(tweet):
    return tweet[5]

def get_body_translation(tweet):
    return tweet[8]

def get_original_language(tweet):
    return tweet[9]

def get_link(tweet):
    return tweet[4]

def get_itemm_id(tweet):
    return tweet[6]

def get_feedsource(tweet):
    return tweet[7]

def atomize(batch):
    atomized_batch = []
    for tweet in batch:
        
        # Extract values from tweet
        id                  = get_id(tweet)
        published           = get_published(tweet)
        author              = get_author(tweet)
        body                = get_body(tweet)
        body_translation    = get_body_translation(tweet)
        original_language   = get_original_language(tweet)
        link                = get_link(tweet)
        item_id             = get_itemm_id(tweet)
        feedsource          = get_feedsource(tweet)

        # Add atoms as tuple to atomized_batch
        atomized_batch.append((
                    id,
                    published,
                    author,
                    body,
                    body_translation,
                    original_language,
                    link,
                    item_id,
                    feedsource
                ))
    return atomized_batch

def insert_atomized_batch(batch, cursor, connection):
    for tweet in batch:
        cursor.execute("INSERT INTO tweets (id, published, author, body, body_translation, original_language, link, item_id, feedsource) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", tweet)
    connection.commit()

# Get cursor for ep_newshub_rss database
ep_newshub_rss_connection = mysql.connector.connect(**ep_newshub_rss_config)
ep_newshub_rss_cursor = ep_newshub_rss_connection.cursor()

# Get cursor for eptwitter database
eptwitter_connection = mysql.connector.connect(**eptwitter_config)
eptwitter_cursor = eptwitter_connection.cursor()

# Load Batch from db
batch = load_batch_from_db(1, 3, ep_newshub_rss_cursor)

# atomize batch
atomized_batch = atomize(batch)

for tweet in atomized_batch:
    print("id:                  " + str(tweet[0]))
    print("published:           " + tweet[1])
    print("author:              " + tweet[2])
    print("body:                " + tweet[3])
    print("body translation:    " + tweet[4])
    print("original language:   " + tweet[5])
    print("link:                " + tweet[6])
    print("item id:             " + tweet[7])
    print("feedsource:          " + tweet[8])
    print("")

# Insert atomized tweet into eptwitter.tweets
# insert_atomized_batch(atomized_batch, eptwitter_cursor, eptwitter_connection)

print("done.")
