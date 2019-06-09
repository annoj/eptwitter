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

import mysql.connector
import argparse

parser = argparse.ArgumentParser(description="Atomize ep_newshub_rss database into eptwitter database.")
parser.add_argument("-b", "--batchsize", type=int, nargs=1, required=True, help="specify the size of the batch to atomize, type is int.")
parser.add_argument("-s", "--startid", type=int, nargs=1, required=True, help="specify the id of the ep_newshub_rss.item to start with, type is int.")
args = parser.parse_args()

batch_size = args.batchsize[0]
start_id = args.startid[0]

ep_newshub_rss_config = {
    'user': 'atomizer',
    'password': 'atomizer_password',
    'host': '127.0.0.1',
    'database': 'ep_newshub_rss',
    'charset': 'utf8mb4',
    'raise_on_warnings': False
}

eptwitter_config = {
    'user': 'atomizer',
    'password': 'atomizer_password',
    'host': '127.0.0.1',
    'database': 'eptwitter',
    'charset': 'utf8mb4',
    'raise_on_warnings': False
}

def load_batch_from_db(start_id, batch_size, cursor):
    cursor.execute(
            "SELECT * FROM items WHERE id >= %s AND id < %s;", 
            (start_id, (start_id + batch_size)))
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

def insert_author(author, cursor, connection):
    cursor.execute(
            "SELECT id FROM meps WHERE name = %s", 
            (author, ))
    author_id = cursor.fetchone()
    if author_id is None:
        print("Author " + author + " was not present in db.")
        cursor.execute(
                "INSERT IGNORE INTO meps (name, party, country, ep_fraction) VALUES (%s, %s, %s, %s)", 
                (author, 1, "ger", 1))
        connection.commit()
        cursor.execute(
                "SELECT id FROM meps WHERE name = %s", 
                (author, ))
        author_id = cursor.fetchone()[0]
    else:
        author_id = author_id[0]
    return author_id

def insert_atomized_batch(batch, cursor, connection):
    for tweet in batch:
        author_id = insert_author(tweet[2], eptwitter_cursor, eptwitter_connection)
        normalized_tweet = (tweet[0], tweet[1], author_id, tweet[3], tweet[4], tweet[5], tweet[6], tweet[7], tweet[8])
        cursor.execute(
                "INSERT IGNORE INTO tweets "
                + "(id, published, author, body, body_translation, original_language, link, item_id, feedsource) "
                + "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                normalized_tweet)
    connection.commit()

# Get cursor for ep_newshub_rss database
ep_newshub_rss_connection = mysql.connector.connect(**ep_newshub_rss_config)
ep_newshub_rss_cursor = ep_newshub_rss_connection.cursor()

# Get cursor for eptwitter database
eptwitter_connection = mysql.connector.connect(**eptwitter_config)
eptwitter_cursor = eptwitter_connection.cursor()

# Load Batch from db
print("Loading batch of size " + str(batch_size) + "...")
batch = load_batch_from_db(start_id, batch_size, ep_newshub_rss_cursor)

# atomize batch
print("Atomizing tweets...")
atomized_batch = atomize(batch)

# for tweet in atomized_batch:
#     print("id:                  " + str(tweet[0]))
#     print("published:           " + tweet[1])
#     print("author:              " + tweet[2])
#     print("body:                " + tweet[3])
#     print("body translation:    " + tweet[4])
#     print("original language:   " + tweet[5])
#     print("link:                " + tweet[6])
#     print("item id:             " + tweet[7])
#     print("feedsource:          " + tweet[8])
#     print("")

# Insert atomized tweet into eptwitter.tweets
print("Inserting atomized tweets into eptwitter.tweets...")
insert_atomized_batch(atomized_batch, eptwitter_cursor, eptwitter_connection)

print("done.")
