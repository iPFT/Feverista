# Feverista

Pythonista application built for the Fever API

## Background
Developed over time using some great examples over the internet including the Pythonista Forums. If the code looks a mish-mash, you can see why!

I normally use the Reeder app to consume my feeds but the inbuilt mercury reader is flakey on a lot of my feeds. Clean text is important to me as I don't want to see all the adverts and videos that distract from the original article text - I just want read and move on. User comments are OK to skim through, but also an unwanted distraction from the main content. It's also great to be able to add and enhance the things that I would like in an app rather than have to rely on another developer, or pay for cluttered services that have things I won't use.

I wanted a way to view articles in a clean way through a self-hosted full-text rss where I can maintain my own site patterns for parsing. I can also have a customised page for the parsed extraction. My python skills were pretty raw when I started this, but I've picked up enough things as I went along and have worked with SQL for years. Working with APIs and pythonista GUI not so much!

Originally I was printing links from a sqlite database within the console, so when I discovered how to pass data through the GUI, it motivated me to build this. It's taken many hours but this was more for the learning curve and 'yes!' moments you get when developing.

So I've built things on what I know and what I've picked up. I'm not an iOS developer so I hope you will help me to build on what I have done and enhance the app further!

Cheers, iPFT

## Key Features:
* Sqlite database and views are built on the fly
* Syncs with a locally stored copy of the Fever API
* Swipe groups right to see feeds
* Ability to read articles with an alternative URL e.g. fulltextrss or mercuryreader
* Ability to manually change article content and group/feed views
* Ability to change how articles are grouped by
* Favicons and People-Friendly dates/times

## Need help with/Possible Enhancements:
* Fix bug where older saved rows dont have titles
* User preferences in the UI, stored in the db
* In app switches for saving and unsaving items
* Make in app swtiches stay at bottom rather than float
* Multiple Fever° Accounts
* Press and hold to Mark above/Below/All as read
* Pull to refresh
* Swipe left/right to Save/Mark as Read/Unread
* General code clean up
* Items to automatically refresh after reading an item
* Item counts to be built from with the app rather than SQL
* Downloading hotlinks but not doing anything with them yet
* Search/Filter functionality, can get this working but will require some GUI changes that are challenging to do in code
* GUI cleanup/smarten up
* Adapt to use internal Reader View
* Adapt the article view to be more like Newsify
* Search functionality across articles
* Local caching of article images
