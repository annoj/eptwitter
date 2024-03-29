

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
# TODO: Handle meps changing fraction and party
# TODO: Extract proper published date
# 
#
#

import mysql.connector
import argparse
import json
from nltk.sentiment.vader import SentimentIntensityAnalyzer

#
# Global variables

# Commandline argument parser
parser = argparse.ArgumentParser(description="Atomize ep_newshub_rss database into eptwitter database.")
parser.add_argument("-b", "--batchsize", type=int, nargs=1, required=True, help="specify the size of the batch to atomize, type is int.")
parser.add_argument("-s", "--startid", type=int, nargs=1, required=True, help="specify the id of the ep_newshub_rss.item to start with, type is int.")
parser.add_argument("-a", "--analyze_sentiment", action="store_true", help="do sentiment analysis on the tweets.")
args = parser.parse_args()

# Command line args
batch_size = args.batchsize[0]
start_id = args.startid[0]

# Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()

# Cache
authors = {}
hashtags = {}

# Database config
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

#
# Function implementations
def load_batch_from_db(start_id, batch_size, cursor):
    cursor.execute(
            "SELECT * FROM items WHERE id >= %s AND id <= %s;", 
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

def get_item_id(tweet):
    return tweet[6]

def get_feedsource(tweet):
    return tweet[7]

def extract_tweet_values(tweet):
    id = get_id(tweet)
    published = get_published(tweet)
    author = get_author(tweet)
    body = get_body(tweet)
    body_translation = get_body_translation(tweet)
    sentiment = analyze_sentiment(body_translation) if args.analyze_sentiment else ""
    original_language = get_original_language(tweet)
    link = get_link(tweet)
    item_id = get_item_id(tweet)
    feedsource = get_feedsource(tweet)

    extracted_tweet = (
            id,
            published,
            author,
            body,
            body_translation,
            original_language,
            sentiment,
            link,
            item_id,
            feedsource
        )

    return extracted_tweet

def extract_hashtags(tweet_body):
     tweet_words = tweet_body.split(' ')
     hastags = []
     for word in tweet_words:
         if (len(word) > 1):
             if (word[0] == '#'):
                 word = word.split('.')[0] # If at end of sentence remove fullstop
                 word = word.split(',')[0] # If before a comma
                 word = word.split(';')[0] # If before semicolon
                 word = word.split(':')[0] # If before :
                 word = word.split('!')[0] # If before !
                 word = word.split('?')[0] # If before ?
                 word = word.split('-')[0] # If before -
                 word = word.split('\\n')[0] # If before newline
                 hastags.append(word)
     return hastags

def atomize(batch):
    atomized_batch = []
    i = 0
    for tweet in batch:
        extracted_tweet = extract_tweet_values(tweet)
        extracted_hashtags = extract_hashtags(extracted_tweet[3])

        atomized_batch.append((
                extracted_tweet,
                extracted_hashtags
            ))
        i += 1
        if (i % 10000 == 0):
            print("Processed " + str(i) + " tweets.")

    return atomized_batch

def analyze_sentiment(text):
    score = analyzer.polarity_scores(text) if text is not None else None
    return score 

def insert_author(author, cursor, connection):
   
    # Try get author from cache
    if author in authors:
        cached_author = authors.get(author)
        author_id = cached_author

    
    # If author was not in cache
    else:

        # Query database
        cursor.execute(
                 "SELECT id FROM meps WHERE name = %s", 
                (author, ))

        author_id = cursor.fetchone()
        
        # If author is not in db insert
        if author_id is None:
            print("Author " + author + " was not present in db.")
            cursor.execute(
                    "INSERT IGNORE INTO meps (name, party, country, ep_fraction) VALUES (%s, %s, %s, %s)", 
                    (author, None, None, None))
            connection.commit()

            # Query for id
            cursor.execute(
                    "SELECT id FROM meps WHERE name = %s", 
                    (author, ))
            author_id = cursor.fetchone()[0]

        # Else if author is in db, just use
        else:
            author_id = author_id[0]

        # Cache author
        authors[author] = author_id

    return author_id

def insert_tweet(tweet, cursor, connection): 
    author_id = insert_author(tweet[2], eptwitter_cursor, connection)
    normalized_tweet = (
            tweet[0], 
            tweet[1], 
            author_id, 
            tweet[3], 
            tweet[4], 
            tweet[5], 
            str(tweet[6]), 
            tweet[7], 
            tweet[8],
            tweet[9]
    )

    cursor.execute(
        "INSERT IGNORE INTO tweets "
        + "(id, published, author, body, body_translation, original_language, sentiment, link, item_id, feedsource) "
        + "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
        normalized_tweet
    )

def insert_hashtag_usage(hashtags, tweet_id, cursor):
    for hashtag in hashtags:
        hashtag_usage = (
            hashtag,
            tweet_id
        )

        cursor.execute(
            "INSERT IGNORE INTO hashtag_usage "
            + "(hashtag, tweet)"
            + "VALUES(%s, %s)",
            hashtag_usage
        )

def insert_atomized_batch(batch, cursor, connection):
    for tweet in batch:
        insert_tweet(tweet[0], cursor, connection)
        insert_hashtag_usage(tweet[1], tweet[0][0], cursor)   

    connection.commit()

#
# Main Script

# Get cursor for ep_newshub_rss database
ep_newshub_rss_connection = mysql.connector.connect(**ep_newshub_rss_config)
ep_newshub_rss_cursor = ep_newshub_rss_connection.cursor()

# Get cursor for eptwitter database
eptwitter_connection = mysql.connector.connect(**eptwitter_config)
eptwitter_cursor = eptwitter_connection.cursor()

# Load Batch from db
print("Loading batch of size " + str(batch_size) + "...")
batch = load_batch_from_db(start_id, batch_size, ep_newshub_rss_cursor)

# Atomize batch
print("Atomizing tweets...")
atomized_batch = atomize(batch)

# Insert atomized tweet into eptwitter.tweets
print("Inserting atomized tweets into eptwitter.tweets...")
insert_atomized_batch(atomized_batch, eptwitter_cursor, eptwitter_connection)

print("done.")
