#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  gunnutfinder.py
#
#  Derived from https://github.com/Wyboth/isReactionaryBot, which is
#  Copyright 2015 Wyboth <www.reddit.com/u/Wyboth>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <http://www.gnu.org/licenses/>.
#


import praw
import sqlite3
import sys
from privatesettings import password, path
from subreddits import gunnutSubreddits
import time
import re


class SubredditData:
    """A log of a user's participation in a gun subreddit."""
    subredditName = ''
    submissionCount = 0
    commentCount = 0
    totalSubmissionKarma = 0
    totalCommentKarma = 0
    submissionPermalinks = None  # List cannot be initialized here!
    commentPermalinks = None  # List cannot be initialized here!


def extract_username(text):
    """Extracts the username from the text of a comment or private message. The bot is summoned on the username found
    immediately after the bot's name."""
    match = username_regex.match(text)
    if match:
        return match.group('username').lower()
    else:
        return None


def has_processed(post):
    """This function returns true if the bot has processed the comment or the private message in question."""
    sqlCursor.execute('SELECT * FROM Identifiers WHERE id=?', (post,))
    if sqlCursor.fetchone() is None:
        return False
    return True


def update_subreddit_data(subredditdata, subreddit, item, is_comment):
    """This takes the submission or comment, and updates its corresponding subredditData class with all of its
    attributes."""
    subreddit_in_list = False
    for i in range(len(subredditdata)):
        if subredditdata[i].subredditName.lower() == subreddit:
            subreddit_in_list = True
            if is_comment:
                subredditdata[i].commentCount += 1
                subredditdata[i].totalCommentKarma += int(item.score)
                if len(subredditdata[i].commentPermalinks) < 8:
                    subredditdata[i].commentPermalinks.append(item.permalink + '?context=10')
            else:
                subredditdata[i].submissionCount += 1
                subredditdata[i].totalSubmissionKarma += int(item.score)
                if len(subredditdata[i].submissionPermalinks) < 8:
                    subredditdata[i].submissionPermalinks.append(item.permalink)
            break
    if not subreddit_in_list:
        newdata = SubredditData()
        newdata.subredditName = item.subreddit.display_name
        if is_comment:
            newdata.commentCount = 1
            newdata.totalCommentKarma = int(item.score)
            newdata.commentPermalinks = [item.permalink + '?context=10']
            newdata.submissionPermalinks = []
        else:
            newdata.submissionCount = 1
            newdata.totalSubmissionKarma = int(item.score)
            newdata.submissionPermalinks = [item.permalink]
            newdata.commentPermalinks = []
        subredditdata.append(newdata)
    return subredditdata


def calculate_gunnuttiness(user):
    """Figures out how much of a gunnut the user is, and returns the reply text."""
    nodata = True
    subredditdata_list = []
    
    praw_user = r.get_redditor(user)
    username = praw_user.name
    submissions = praw_user.get_submitted(limit=1000)
    comments = praw_user.get_comments(limit=1000)
    
    for submission in submissions:
        subreddit = submission.subreddit.display_name.lower()
        if subreddit in [x.lower() for x in gunnutSubreddits]:
            nodata = False
            subredditdata_list = update_subreddit_data(subredditdata_list, subreddit, submission, False)
    
    for comment in comments:
        subreddit = comment.subreddit.display_name.lower()
        if subreddit in [x.lower() for x in gunnutSubreddits]:
            nodata = False
            subredditdata_list = update_subreddit_data(subredditdata_list, subreddit, comment, True)
    
    if nodata:
        return 'Nothing found for ' + username + '.'
    
    score = 0
    replytext = username + ' post history contains participation in the following subreddits:\n\n'
    for subredditData in subredditdata_list:
        replytext += '[/r/' + subredditData.subredditName + '](' + 'http://np.reddit.com/r/' +\
                     subredditData.subredditName + '): '
        if len(subredditData.submissionPermalinks) > 0:
            replytext += str(subredditData.submissionCount) + ' posts ('
            for i in range(len(subredditData.submissionPermalinks)):
                replytext += '[' + str(i+1) + '](' + subredditData.submissionPermalinks[i].replace('www.', 'np.') + '), '
            replytext = replytext[:-2] + '), **combined score: ' + str(subredditData.totalSubmissionKarma) + '**'
            if len(subredditData.commentPermalinks) > 0:
                replytext += '; '
        if len(subredditData.commentPermalinks) > 0:
            replytext += str(subredditData.commentCount) + ' comments ('
            for i in range(len(subredditData.commentPermalinks)):
                replytext += '[' + str(i+1) + '](' + subredditData.commentPermalinks[i].replace('www.', 'np.') + '), '
            replytext = replytext[:-2] + '), **combined score: ' + str(subredditData.totalCommentKarma) + '**'
        replytext += '.\n\n'
        score += subredditData.totalSubmissionKarma + subredditData.totalCommentKarma
    
    replytext += '---\n\n###Total score: ' + str(score) + '\n\n###Chance of being a gunnut: '
    if score > 0:
        replytext += str((score + 1) ** 3) + '%.'
    else:
        replytext += '0%.'
    replytext += '\n\n---\n\nI am a bot. Only the past 1,000 posts and comments are fetched. If I am misbehaving send' \
                 'my [Creator](https://np.reddit.com/message/compose/?to=sasnfbi1234) a message.'
    return replytext


def handle_request(request):
    """Handles a user's comment or private message requesting the bot to investigate a user's gunnuttiness."""
    if not has_processed(request.id):
        user = extract_username(request.body)
        if user is not None:
            try:
                if user == 'gunnutfinder':  # For smartasses.
                    request.reply('Nice try.')
                    sqlCursor.execute('INSERT INTO Identifiers VALUES (?)', (request.id,))
                    print(time.ctime() + ': Received request to check self.')
                else:
                    request.reply(calculate_gunnuttiness(user))
                    sqlCursor.execute('INSERT INTO Identifiers VALUES (?)', (request.id,))
                    print(time.ctime() + ': Received and successfully processed request to check user {0}'.format(user))
            except praw.errors.NotFound:
                request.reply('User {0} not found.'.format(user))
                sqlCursor.execute('INSERT INTO Identifiers VALUES (?)', (request.id,))
                print(time.ctime() + ': Received request to check user {0}. Failed to find user.'.format(user),
                      file=sys.stderr)
            sqlConnection.commit()


def main():
    r.login('gunnutfinder', password)
    print(time.ctime() + ': Logged in as /u/gunnutfinder', file=sys.stdout)
    while True:
        try:
            for mention in r.get_mentions():
                handle_request(mention)
            for message in r.get_messages():
                handle_request(message)
        except Exception as e:
            print(e, file=sys.stderr)
        time.sleep(120)


username_regex = re.compile(
    r'^(/u/gunnutfinder)?\s*(?:/?u/)?(?P<username>\w+)\s*$',
    re.IGNORECASE | re.MULTILINE
)

sqlConnection = sqlite3.connect(path + 'database.db')
sqlCursor = sqlConnection.cursor()
sqlCursor.execute('CREATE TABLE IF NOT EXISTS Identifiers (id text)')

r = praw.Reddit(user_agent='A program that checks if a user is a gun nut.')

sys.stdout = open(path + 'log.txt', 'a')
sys.stderr = open(path + 'error.txt', 'a')

if __name__ == '__main__':
    main()
