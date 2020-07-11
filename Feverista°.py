# coding: utf-8

'''
Name: Feverista°
Author: iPFT
Purpose: Pythonista News Reader app that syncs with the Fever° API
Python: 3.6
Version: 1.0

Developed over time using some great examples over the internet including the Pythonista Forums. If the code looks a mish-mash, you can see why!

I normally use the Reeder app to consume my feeds but the inbuilt mercury reader is flakey on a lot of my feeds. Clean text is important to me as I don't want to see all the adverts and videos that distract from the original article text - I just want read and move on. User comments are OK to skim through, but also an unwanted distraction from the main content. It's also great to be able to add and enhance the things that I would like in an app rather than have to rely on another developer, or pay for cluttered services that have things I won't use.

I wanted a way to view articles in a clean way through a self-hosted full-text rss where I can maintain my own site patterns for parsing. I can also have a customised page for the parsed extraction. My python skills were pretty raw when I started this, but I've picked up enough things as I went along and have worked with SQL for years. Working with APIs and pythonista GUI not so much!

Originally I was printing links from a sqlite database within the console, so when I discovered how to pass data through the GUI, it motivated me to build this. It's taken many hours but this was more for the learning curve and 'yes!' moments you get when developing.

So I've built things on what I know and what I've picked up. I'm not an iOS developer so I hope you will help me to build on what I have done and enhance the app further!

Cheers, iPFT

Key Features:
    Sqlite database and views are built on the fly
    Syncs with a locally stored copy of the Fever API
    Swipe groups right to see feeds
    Ability to read articles with an alternative URL e.g. fulltextrss or mercuryreader
    Ability to manually change article content and group/feed views
    Ability to change how articles are grouped by
    Favicons and People-Friendly dates/times

Need help with/Possible Enhancements:
    Fix bug where older saved rows dont have titles
    User preferences in the UI, stored in the db
    In app switches for saving and unsaving items
    Make in app swtiches stay at bottom rather than float
    Multiple Fever° Accounts
    Press and hold to Mark above/Below/All as read
    Pull to refresh
    Swipe left/right to Save/Mark as Read/Unread
    General code clean up
    Items to automatically refresh after reading an item
    Item counts to be built from with the app rather than SQL
    Downloading hotlinks but not doing anything with them yet
    Search/Filter functionality, can get this working but will require some GUI changes that are challenging to do in code
    GUI cleanup/smarten up
    Adapt to use internal Reader View
    Adapt the article view to be more like Newsify
    Search functionality across articles
    Local caching of article images
'''

import sqlite3
import ui
import requests
import hashlib
from datetime import datetime, timedelta
import time
from dateutil.parser import parse as parse_date
import base64
from objc_util import *
#import gestures

app_name = 'Feverista°'
# Input the URL of your Fever API
baseurl = ''
# Leave blank if you don't use a text reader
readurl = ''
# email and password you use to login to Fever
email = ''
pword = ''
api_key = hashlib.md5(str(email + ':' + pword).encode('utf-8')).hexdigest()
payload = {'api_key': api_key}

# Change these options depending on the view you want. Would be better in the UI
# Saved Archived Unread All Items
view_type = 'Unread'
group_by = 'date'  # date group feed
# item_created_on_time feed_id item_created_minsago
item_sort_by = 'item_created_on_time'
item_sort_direction = 'ASC'  # DESC ASC

# what to call and where to store the database
fvr_db = 'fvr.db'

# ******** End of User Credentials ******** #

timestamp = int(time.time())


def createDb():
    conn = sqlite3.connect(fvr_db)

    conn.execute('''CREATE TABLE IF NOT EXISTS groups
           (id INTEGER PRIMARY KEY NOT NULL,
           title TEXT NOT NULL);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS feeds
        (id INTEGER PRIMARY KEY NOT NULL,
        favicon_id INTEGER NOT NULL,
        title TEXT,
        url TEXT,
        site_url TEXT,
        is_spark INTEGER NOT NULL,
        last_updated_on_time TIMESTAMP);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS feeds_group
        (group_id INTEGER NOT NULL,
        feed_id INTEGER NOT NULL);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS favicons
        (id INTEGER PRIMARY KEY NOT NULL,
        data TEXT NOT NULL);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS items
        (id INTEGER PRIMARY KEY NOT NULL,
        feed_id INTEGER,
        title TEXT,
        author TEXT,
        html TEXT,
        url TEXT,
        is_saved INTEGER,
        is_read INTEGER,
        created_on_time TIMESTAMP);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS links
        (id INTEGER PRIMARY KEY NOT NULL,
        feed_id INTEGER,
        item_id INTEGER,
        temperature NUMERIC,
        is_item NUMERIC,
        is_local NUMERIC,
        is_saved NUMERIC,
        title TEXT,
        url TEXT,
        item_ids TEXT);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS last_refreshed_on_time
        (last_refreshed_on_time TIMESTAMP);''')

    conn.execute('''CREATE UNIQUE INDEX IF NOT EXISTS "idxItemId" ON "items" (
    	"id"	ASC
    )''')

    conn.execute('''CREATE INDEX IF NOT EXISTS "idxLinksId" ON "links" (
    	"id"	ASC
    )''')

    conn.close()


def createViews():
    conn = sqlite3.connect(fvr_db)

    conn.execute('''DROP VIEW IF EXISTS `vwSaved`''')
    conn.execute('''CREATE VIEW IF NOT EXISTS `vwSaved` AS
    SELECT
    groups.id as group_id, groups.title as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, count (*) OVER() as item_count, items.url as item_url,
    datetime(items.created_on_time, 'unixepoch', 'localtime')  as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE items.is_saved = 1
    ORDER BY items.created_on_time ASC''')
    conn.commit()

    conn.execute('''DROP VIEW IF EXISTS `vwUnread`''')
    conn.execute('''CREATE VIEW IF NOT EXISTS `vwUnread` AS
    SELECT
    groups.id as group_id, groups.title as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, count (*) OVER() as item_count, items.url as item_url,
    datetime(items.created_on_time, 'unixepoch', 'localtime')  as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE items.is_read = 0 AND feeds.is_spark = 0
    ORDER BY items.created_on_time ASC''')
    conn.commit()

    conn.execute('''DROP VIEW IF EXISTS `vwAllItems`''')
    conn.execute('''CREATE VIEW IF NOT EXISTS `vwAllItems` AS
    SELECT
    groups.id as group_id, groups.title as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, count (*) OVER() as item_count, items.url as item_url,
    datetime(items.created_on_time, 'unixepoch', 'localtime')  as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE (items.is_saved = 1 or feeds.is_spark = 0)
    ORDER BY items.created_on_time ASC''')
    conn.commit()

    conn.execute('''DROP VIEW IF EXISTS `vwArchive`''')
    conn.execute('''CREATE VIEW IF NOT EXISTS `vwArchive` AS
    SELECT
    groups.id as group_id, groups.title as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, count (*) OVER() as item_count, items.url as item_url,
    datetime(items.created_on_time, 'unixepoch', 'localtime')  as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE items.is_read = 1 AND items.is_saved = 0
    ORDER BY items.created_on_time ASC''')
    conn.commit()

    conn.execute('''DROP VIEW IF EXISTS `vwFever`''')
    conn.execute('''CREATE VIEW IF NOT EXISTS `vwFever` AS
    SELECT
    CASE WHEN items.is_saved = 1 THEN 1 ELSE 0 END as saved,
    CASE WHEN items.is_read = 0 AND feeds.is_spark = 0 THEN 1 ELSE 0 END as unread,
    CASE WHEN items.is_saved = 1 or feeds.is_spark = 0 THEN 1 ELSE 0 END as all_items,
    CASE WHEN items.is_read = 1 AND items.is_saved = 0 THEN 1 ELSE 0 END as archive,
    CASE WHEN feeds.is_spark = 1 THEN 1 ELSE 0 END as spark,
    groups.id as group_Id, groups.title as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, count (*) OVER() as item_count, items.url as item_url,
    datetime(items.created_on_time, 'unixepoch', 'localtime')  as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    ORDER BY items.created_on_time ASC''')
    conn.commit()

    conn.execute('''DROP VIEW IF EXISTS `vwFever2`''')
    conn.execute('''CREATE VIEW IF NOT EXISTS `vwFever2` AS
    SELECT
    'Saved' as view_type,
    coalesce(groups.id,'0') as group_id, coalesce(groups.title, 'No Group')  as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, items.author as item_author, items.html as item_html, count (*) OVER() as item_count, items.url as item_url,
    strftime('%Y-%m-%d %H:%M:%S', datetime(items.created_on_time, 'unixepoch', 'localtime')) as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE items.is_saved = 1
    UNION ALL
    SELECT
    'Unread' as view_type,
    coalesce(groups.id,'0') as group_id, coalesce(groups.title, 'No Group')  as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, items.author as item_author, items.html as item_html, count (*) OVER() as item_count, items.url as item_url,
    strftime('%Y-%m-%d %H:%M:%S', datetime(items.created_on_time, 'unixepoch', 'localtime')) as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE items.is_read = 0 AND feeds.is_spark = 0
    UNION ALL
    SELECT
    'All Items' as view_type,
    coalesce(groups.id,'0') as group_id, coalesce(groups.title, 'No Group')  as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, items.author as item_author, items.html as item_html, count (*) OVER() as item_count, items.url as item_url,
    strftime('%Y-%m-%d %H:%M:%S', datetime(items.created_on_time, 'unixepoch', 'localtime')) as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE (items.is_saved = 1 or feeds.is_spark = 0)
    UNION ALL
    SELECT
    'Archived' as view_type,
    coalesce(groups.id,'0') as group_id, coalesce(groups.title, 'No Group')  as group_title, count (*) OVER(PARTITION BY groups.id) as group_count,
    feeds.id as feed_id, feeds.title as feed_title, count (*) OVER(PARTITION BY feeds.id) as feed_count,  favicons.data as feed_favicon,
    items.id as item_id, items.title as item_title, items.author as item_author, items.html as item_html, count (*) OVER() as item_count, items.url as item_url,
    strftime('%Y-%m-%d %H:%M:%S', datetime(items.created_on_time, 'unixepoch', 'localtime')) as item_created_on_time,
    (strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60 as item_created_minsago
    FROM items
    LEFT OUTER JOIN feeds
    ON items.feed_id = feeds.id
    LEFT OUTER JOIN favicons
    ON feeds.favicon_id = favicons.id
    LEFT OUTER JOIN feeds_group
    ON feeds.id = feeds_group.feed_id
    LEFT OUTER JOIN groups
    ON feeds_group.group_id = groups.id
    WHERE items.is_read = 1 AND items.is_saved = 0''')
    conn.commit()


def refreshAll():
    conn = sqlite3.connect(fvr_db)
    c = conn.cursor()
    url = baseurl + '&groups&feeds&favicons&saved_item_ids&unread_item_ids&links&offset=0&range=7'
    r = requests.post(url, payload).json()
    last_refreshed = r['last_refreshed_on_time']
    unread_items = r['unread_item_ids']
    saved_items = r['saved_item_ids']

    progress = 'Syncing...'
    # print(progress)

    progress = 'Updating RefreshTime...'
    # print(progress)
    conn.execute("DELETE FROM last_refreshed_on_time;")
    conn.execute('insert into last_refreshed_on_time values (?)',
                 (last_refreshed,))

    # save to text file if needed
    # with open('last_refreshed.txt', 'w') as f:
    #    f.write(last_refreshed)

    progress = 'Purging old items...'
    # print(progress)
    conn.execute("DELETE FROM items WHERE is_saved = 0 and is_read = 1 and ((strftime('%s','now') - strftime('%s', datetime(items.created_on_time, 'unixepoch', 'localtime')))/60) >=4320;")

    progress = 'Getting items'
    # print(progress)
    checkItemArray = [1]
    while len(checkItemArray) != 0:

        c.execute("SELECT max(id) FROM items;")
        since_id = str(c.fetchone()[0])
        # print("since_id: " + since_id)

        url = baseurl + '&items&since_id=' + since_id
        r2 = requests.post(url, payload).json()
        checkItemArray = (r2['items'])

        for data in r2['items']:
            conn.execute('insert or ignore into items values (?,?,?,?,?,?,?,?,?)', [
                         data['id'], data['feed_id'], data['title'], data['author'], data['html'], data['url'], data['is_saved'], data['is_read'], data['created_on_time']])

    progress = 'Updating groups'
    # print(progress)
    conn.execute("DELETE FROM groups;")

    for data in r['groups']:
        conn.execute('insert into groups values (?,?)',
                     [data['id'], data['title']])

    progress = 'Updating feeds'
    # print(progress)
    conn.execute("DELETE FROM feeds;")

    for data in r['feeds']:
        conn.execute('insert into feeds values (?,?,?,?,?,?,?)', [
                     data['id'], data['favicon_id'], data['title'], data['url'], data['site_url'], data['is_spark'], data['last_updated_on_time']])

    progress = 'Updating feeds group'
    # print(progress)
    conn.execute("DELETE FROM feeds_group;")

    for data in r['feeds_groups']:
        parsed_feed_ids = data['feed_ids'].split(',')
        for feed_id in parsed_feed_ids:
            conn.execute('insert into feeds_group values (?,?)',
                         [data['group_id'], feed_id])

    progress = 'Updating favicons'
    # print(progress)
    conn.execute("DELETE FROM favicons;")

    for data in r['favicons']:
        conn.execute('insert into favicons values (?,?)',
                     [data['id'], data['data']])

    progress = 'Updating links'
    # print(progress)
    conn.execute("DELETE FROM links;")

    for data in r['links']:
        conn.execute('insert into links values (?,?,?,?,?,?,?,?,?,?)', [
                     data['id'], data['feed_id'], data['item_id'], data['temperature'], data['is_item'], data['is_local'], data['is_saved'], data['title'], data['url'], data['item_ids']])

    progress = 'Updating unread items'
    # print(progress)
    c.execute('''UPDATE items SET is_read = 1 WHERE Id not in (''' +
              unread_items + ''') and is_read = 0;''')
    c.execute('''UPDATE items SET is_read = 0 WHERE Id in (''' +
              unread_items + ''') and is_read = 1;''')

    progress = 'Updating saved'
    # print(progress)
    c.execute('''UPDATE items SET is_saved = 1 WHERE Id in (''' +
              saved_items + ''') and is_saved = 0;''')
    c.execute('''UPDATE items SET is_saved = 0 WHERE Id not in (''' +
              saved_items + ''') and is_saved = 1;''')

    progress = "All Done!"
    conn.commit()
    conn.close()


def encodeString(str):
    str = str.replace('_eq_', '=')
    str = str.replace('_and_', '&')
    str = str.replace('_hash_', '#')
    str = str.replace('&apos;', '\'')
    str = str.replace('&middot;', '•')
    return str


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(round(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(round(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(round(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(round(day_diff)) + " days ago"
    if day_diff < 31:
        if round(day_diff / 7) == 1:
            return str(round(day_diff / 7)) + " week ago"
        else:
            return str(round(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        if round(day_diff / 30) == 1:
            return str(round(day_diff / 30)) + " month ago"
        else:
            return str(round(day_diff / 30)) + " months ago"
    if round(day_diff / 365) == 1:
        return str(round(day_diff / 365)) + " year ago"
    else:
        return str(round(day_diff / 365)) + " years ago"


def getData(view_type, group_id, feed_id):
    conn = sqlite3.connect(fvr_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM vwFever2 WHERE view_type like '" + view_type + "' and group_id like '" + str(group_id) +
              "' AND feed_id like '" + str(feed_id) + "' ORDER BY " + item_sort_by + ' ' + item_sort_direction)
    rows = c.fetchall()
    #data = []
    if len(rows) > 0:
        data.append(
            {'title': view_type + ' (' + str(rows[0]['item_count']) + ')', 'group_id': '%', 'feed_id': '%'})
        for row in rows:
            data.append(
                {
                    'feed_favicon': row['feed_favicon'],
                    'title': encodeString(row['item_title']),
                    'url': row['item_url'],
                    'dt': row['item_created_on_time'],
                    'id': row['item_id'],
                    'item_author': row['item_author'],
                    'item_html': row['item_html'],
                    # 'is_saved': row['is_saved'],
                    'group_id': row['group_id'],
                    'group_title': row['group_title'],
                    'feed_id': row['feed_id'],
                    'feed_title': row['feed_title']
                })
    conn.close()
    return data


def getGroups():
    conn = sqlite3.connect(fvr_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM vwFever2 WHERE view_type like '" +
              view_type + "' GROUP by group_id ORDER BY view_type, group_title")
    rows = c.fetchall()
    groups = []
    if len(rows) > 0:
        groups.append(
            {'feed_favicon': '☠︝',
             'title': view_type + ' (' + str(rows[0]['item_count']) + ')', 'group_id': '%', 'feed_id': '%'})
        for row in rows:
            groups.append(
                {
                    'feed_favicon': '💀',
                    'title': encodeString(row['group_title']) + ' (' + str(row['group_count']) + ')',
                    'url': '',
                    'dt': '',
                    'id': '',
                    'item_author': '',
                    'item_html': '',
                    'group_id': row['group_id'],
                    'feed_id': '%'
                })
    conn.close()
    return groups


def getFeeds(group_id, feed_id):
    conn = sqlite3.connect(fvr_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM vwFever2 WHERE view_type like '" + view_type +
              "' and group_id like '" + str(group_id) + "' GROUP BY feed_id ORDER BY feed_title")
    rows = c.fetchall()
    feeds = []
    if len(rows) > 0:
        feeds.append(
            {'feed_favicon': '👾', 'title':  view_type + ' Feeds (' + str(rows[0]['group_count']) + ')', 'group_id': group_id, 'feed_id': feed_id})
        for row in rows:
            feeds.append(
                {
                    'feed_favicon': row['feed_favicon'],
                    'title': encodeString(row['feed_title']) + ' (' + str(row['feed_count']) + ')',
                    'url': '',
                    'dt': '',
                    'id': '',
                    'item_author': '',
                    'item_html': '',
                    'group_id': row['group_id'],
                    'feed_id': row['feed_id']
                })
    conn.close()
    return feeds


def getItems(group_id, feed_id):
    conn = sqlite3.connect(fvr_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM vwFever2 WHERE view_type like '" + view_type + "' and group_id like '" +
              str(group_id) + "' AND feed_id like '" + str(feed_id) + "' ORDER BY " + item_sort_by + ' ' + item_sort_direction)
    rows = c.fetchall()
    items = []
    if len(rows) > 0:
        for row in rows:
            items.append(
                {
                    'feed_favicon': row['feed_favicon'],
                    'title': encodeString(row['item_title']),
                    'url': row['item_url'],
                    'dt': row['item_created_on_time'],
                    'id': row['item_id'],
                    'item_author': row['item_author'],
                    'item_html': row['item_html'],
                    # 'item_is_saved': row['item_is_saved'],
                    'group_id': row['group_id'],
                    'group_title': row['group_title'],
                    'feed_id': row['feed_id'],
                    'feed_title': row['feed_title']
                })
    conn.close()
    return items


def openLink(url):
    wv = ui.WebView()
    wv.load_url(url)
    tableview.navigation_view.push_view(wv)


def markAsRead(mark, id):
    conn = sqlite3.connect(fvr_db)
    c = conn.cursor()

    if mark == 'item':
        payload = {'api_key': api_key, 'mark': mark, 'as': 'read', 'id': id}
        c.execute('UPDATE items SET is_read = 1 WHERE id = ?', (id,))
    elif mark == 'group':
        payload = {'api_key': api_key, 'mark': mark,
                   'as': 'read', 'id': id, 'before': timestamp}
        c.execute('UPDATE items SET is_read = 1 WHERE id in (SELECT items.id FROM items LEFT OUTER JOIN feeds ON items.feed_id = feeds.id LEFT OUTER JOIN feeds_group ON feeds.id = feeds_group.feed_id LEFT OUTER JOIN groups ON feeds_group.group_id = groups.id WHERE items.is_read = 0 and feeds.is_spark = 0 and feeds_group.group_id =?)', (id,))

    r = requests.post(baseurl, payload)
    conn.commit()


def sync_action(sender):
    refreshAll()


def feed_action(fd):
    print('feed')


def group_action(grp):
    print('group')


def segment_action(sender):
    seg_name = sender.segments[sender.selected_index]
    print(seg_name + ' has been selected')
    view_type = seg_name


class MyTableView(object):
    def __init__(self):
        switches = ui.SegmentedControl(frame=(50, 700, 300, 29))
        switches.segments = ['Starred', 'Unread', 'All Items']

        switches.selected_index = 1
        switches.action = segment_action

        self.list = getGroups()
        self.tv = ui.TableView()
        self.tv.name = view_type + ' Groups'
        self.tv.delegate = self
        self.tv.data_source = self

        nv = ui.NavigationView(self.tv)
        nv.name = app_name

        sync_button = ui.ButtonItem()
        sync_button.title = '🔄'
        sync_button.tint_color = 'red'
        sync_button.action = sync_action
        nv.left_button_items = [sync_button]

        feed_button = ui.ButtonItem()
        feed_button.title = 'Feed'
        feed_button.tint_color = 'green'
        feed_button.action = feed_action

        group_button = ui.ButtonItem()
        group_button.title = 'Group'
        group_button.tint_color = 'blue'
        group_button.action = group_action

        nv.right_button_items = [feed_button, group_button]
        nv.add_subview(switches)
        nv.present('fullscreen')

    def tableview_did_select(self, tableview, section, row):
        tv = ui.TableView()
        tv.title = view_type + ' ' + str(self.list[row]['title'])
        tv.group_id = str(self.list[row]['group_id'])
        tv.feed_id = str(self.list[row]['feed_id'])
        item_ds = ItemTableView(tv.group_id, tv.feed_id)
        tv.data_source = item_ds
        tv.delegate = item_ds
        tableview.navigation_view.push_view(tv)
        tv.reload()

    def tableview_number_of_sections(self, tableview):
        return 1

    def tableview_number_of_rows(self, tableview, section):
        return len(self.list)

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell('subtitle')
        cell.text_label.text = self.list[row]['title']
        favicon = ui.ImageView(frame=(2, 10, 16, 16))
        favicon.image = ui.Image.from_data(base64.decodebytes(
            self.list[row]['feed_favicon'].partition('base64,')[2].encode('utf-8')), 2)
        cell.content_view.add_subview(favicon)
        cell.text_label.number_of_lines = 0
        return cell

    def tableview_title_for_delete_button(self, tableview, section, row):
        return 'Feeds>'

    def tableview_can_delete(self, tableview, section, row):
        return True

    def tableview_delete(self, tableview, section, row):
        tv = ui.TableView()
        tv.title = str(self.list[row]['title'])
        tv.group_id = str(self.list[row]['group_id'])
        tv.feed_id = str(self.list[row]['feed_id'])
        sub_ds = SubTableView(tv.group_id, tv.feed_id)
        tv.data_source = sub_ds
        tv.delegate = sub_ds
        tableview.navigation_view.push_view(tv)


class SubTableView(object):
    def __init__(self, group_id, feed_id):
        self.feeds = getFeeds(group_id, feed_id)
        self.tv = ui.TableView()
        self.tv.delegate = self
        self.tv.data_source = self

    def tableview_did_select(self, tableview, section, row):
        tv = ui.TableView()
        tv.title = view_type + ' ' + str(self.feeds[row]['title'])
        tv.group_id = str(self.feeds[row]['group_id'])
        tv.feed_id = str(self.feeds[row]['feed_id'])
        item_ds = ItemTableView(tv.group_id, tv.feed_id)
        tv.data_source = item_ds
        tv.delegate = item_ds
        tableview.navigation_view.push_view(tv)
        tv.reload()

    def tableview_number_of_sections(self, tableview):
        return 1

    def tableview_number_of_rows(self, tableview, section):
        return len(self.feeds)

    def tableview_cell_for_row(self, tableview, section, row):
        cell = ui.TableViewCell('subtitle')
        cell.text_label.text = self.feeds[row]['title']
        favicon = ui.ImageView(frame=(2, 10, 16, 16))
        favicon.image = ui.Image.from_data(base64.decodebytes(
            self.feeds[row]['feed_favicon'].partition('base64,')[2].encode('utf-8')), 2)
        cell.content_view.add_subview(favicon)
        cell.text_label.number_of_lines = 0
        return cell


class ItemTableView(object):
    def __init__(self, group_id, feed_id):
        self.items = getItems(group_id, feed_id)
        self.sections = {}
        self.section_indices = []

        if feed_id is None:
            return
        for row in self.items:
            if group_by == 'date':
                sectn = pretty_date(parse_date(row['dt']))
                sectn = sectn.upper()
            elif group_by == 'group':
                sectn = row['group_title']
            elif group_by == 'feed':
                sectn = row['feed_title']

            if sectn in self.sections:
                self.sections[sectn].append(row)
            else:
                self.sections[sectn] = [row]
                self.section_indices.append(sectn)

        self.tv = ui.TableView()
        self.tv.delegate = self
        self.tv.data_source = self

    def tableview_did_select(self, tableview, section, row):
        entry = self.sections[self.section_indices[section]][row]
        tv = ui.TableView()
        #tv.name = self.items[row]['title']
        tv.name = entry['title']
        tv.delegate = self

        url = readurl + str(entry['url'])
        wv = ui.WebView()
        wv.load_url(url)
        tableview.navigation_view.push_view(wv)

        markAsRead('item', str(entry['id']))

    def tableview_number_of_sections(self, tableview):
        return len(self.sections)

    def tableview_number_of_rows(self, tableview, section):
        return len(self.sections[self.section_indices[section]])

    def tableview_cell_for_row(self, tableview, section, row):
        entry = self.sections[self.section_indices[section]][row]

        cell = ui.TableViewCell('subtitle')
        cell.text_label.text = entry['title']

        if len(entry['item_author']) > 1:
            author = ' • by ' + entry['item_author']
        else:
            author = ''

        dt = parse_date(entry['dt']).strftime("%H:%M")

        cell.detail_text_label.text = entry['feed_title'] + \
            author + ' • ' + dt

        favicon = ui.ImageView(frame=(2, 10, 16, 16))
        favicon.image = ui.Image.from_data(base64.decodebytes(
            entry['feed_favicon'].partition('base64,')[2].encode('utf-8')), 2)
        cell.content_view.add_subview(favicon)

        cell.text_label.number_of_lines = 0
        return cell

    def tableview_title_for_header(self, tableview, section):
        return str(self.section_indices[section])

    def tableview_title_for_delete_button(self, tableview, section, row):
        return 'Save>'

    def tableview_can_delete(self, tableview, section, row):
        return True

    def tableview_delete(self, tableview, section, row):
        entry = self.sections[self.section_indices[section]][row]
        print('Save', entry['id'])


if __name__ == '__main__':
    createDb()
    createViews()
    MyTableView()
