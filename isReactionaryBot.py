#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  isReactionaryBot.py
#  
#  Copyright 2015 Wyboth <www.reddit.com/u/Wyboth>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  



import praw, sqlite3, sys
from isReactionaryBotPrivateSettings import password, path
from isReactionaryBotSubreddits import reactionarySubreddits
from time import sleep

class SubredditData:#A log of a user's participation in a reactionary subreddit.
	subredditName = ''
	submissionCount = 0
	commentCount = 0
	totalSubmissionKarma = 0
	totalCommentKarma = 0
	submissionPermalinks = None#List cannot be initialized here!
	commentPermalinks = None#List cannot be initialized here!

def extractUsername(text):#Extracts the username to check for reactionariness from the text of a comment or private message. The only proper way to summon the bot is to have "/u/isreactionarybot foobar" in its own paragraph, with nothing before or after it.
	lowercaseText = text.lower()
	paragraphs = lowercaseText.splitlines()
	for paragraph in paragraphs:
		if paragraph.find('/u/isreactionarybot ') == 0:
			username = paragraph[20:]
			if username.find(' ') == -1 and len(username) > 0:
				if username.find('/u/') == 0:
					return username[3:]
				elif username.find('u/') == 0:
					return username[2:]
				else:
					return username
	return None

def isValidUsername(name):
	isValid = False
	
	try:
		redditor = r.get_redditor(name)
		submissions = redditor.get_submitted()
		for submission in submissions:
			isValid = True
			break
	except:
		pass
	
	return isValid

def hasProcessed(id):#This function returns true if the bot has processed the comment or the private message in question. If it has not processed it, it is about to, so it inserts the id of the comment or private message into a SQL database, so it will not process it twice.
	hasProcessed = True
	
	sqlCursor.execute('SELECT * FROM Identifiers WHERE id=?', (id,))
	if sqlCursor.fetchone() == None:
		hasProcessed = False
		sqlCursor.execute('INSERT INTO Identifiers VALUES (?)', (id,))
	
	sqlConnection.commit()
	return hasProcessed

def updateSubredditData(subredditDataList, subreddit, item, isComment):#This takes the submission or comment, and updates its corresponding subredditData class with all of its attributes.
	subredditInList = False
	for i in range( len(subredditDataList) ):
		if subredditDataList[i].subredditName.lower() == subreddit:
			subredditInList = True
			if isComment:
				subredditDataList[i].commentCount += 1
				subredditDataList[i].totalCommentKarma += int(item.score)
				if len(subredditDataList[i].commentPermalinks) < 8:
					subredditDataList[i].commentPermalinks.append( str( r.get_info( thing_id=item.link_id ).permalink ) + str(item.id) + '?context=10' )
			else:
				subredditDataList[i].submissionCount += 1
				subredditDataList[i].totalSubmissionKarma += int(item.score)
				if len(subredditDataList[i].submissionPermalinks) < 8:
					subredditDataList[i].submissionPermalinks.append(str(item.permalink))
			break
	if not subredditInList:
		newSubredditData = SubredditData()
		newSubredditData.subredditName = str(item.subreddit)
		if isComment:
			newSubredditData.commentCount = 1
			newSubredditData.totalCommentKarma = int(item.score)
			newSubredditData.commentPermalinks = [ str( r.get_info( thing_id=item.link_id ).permalink ) ]
			newSubredditData.submissionPermalinks = []
		else:
			newSubredditData.submissionCount = 1
			newSubredditData.totalSubmissionKarma = int(item.score)
			newSubredditData.submissionPermalinks = [str(item.permalink)]
			newSubredditData.commentPermalinks = []
		subredditDataList.append(newSubredditData)
	return subredditDataList

def calculateReactionariness(user):#Figure out how reactionary the user is, and return the text to reply with.
	mixedCaseUsername = ''
	nothingToReport = True
	subredditDataList = []
	
	userObj = r.get_redditor(user)
	userSubmissions = userObj.get_submitted(limit=1000)
	userComments = userObj.get_comments(limit=1000)
	
	for submission in userSubmissions:
		if len(mixedCaseUsername) == 0:
			mixedCaseUsername = str(submission.author)
		subreddit = str(submission.subreddit).lower()
		if subreddit in [x.lower() for x in reactionarySubreddits]:
			nothingToReport = False
			subredditDataList = updateSubredditData(subredditDataList, subreddit, submission, False)
	
	for comment in userComments:
		if len(mixedCaseUsername) == 0:
			mixedCaseUsername = str(comment.author)
		subreddit = str(comment.subreddit).lower()
		if subreddit in [x.lower() for x in reactionarySubreddits]:
			nothingToReport = False
			subredditDataList = updateSubredditData(subredditDataList, subreddit, comment, True)
	
	if nothingToReport:
		return 'Nothing found for ' + mixedCaseUsername + '.'
	
	totalScore = 0
	replyText = mixedCaseUsername + ' post history contains participation in the following subreddits:\n\n'
	for subredditData in subredditDataList:
		replyText += '/r/' + subredditData.subredditName + ': '
		if len(subredditData.submissionPermalinks) > 0:
			replyText += str(subredditData.submissionCount) + ' posts ('
			for i in range( len(subredditData.submissionPermalinks) ):
				replyText += '[' + str(i+1) + '](' + subredditData.submissionPermalinks[i] + '), '
			replyText = replyText[:-2] + '), **combined score: ' + str(subredditData.totalSubmissionKarma) + '**'
			if len(subredditData.commentPermalinks) > 0:
				replyText += '; '
		if len(subredditData.commentPermalinks) > 0:
			replyText += str(subredditData.commentCount) + ' comments ('
			for i in range( len(subredditData.commentPermalinks) ):
				replyText += '[' + str(i+1) + '](' + subredditData.commentPermalinks[i] + '), '
			replyText = replyText[:-2] + '), **combined score: ' + str(subredditData.totalCommentKarma) + '**'
		replyText += '.\n\n'
		totalScore += subredditData.totalSubmissionKarma + subredditData.totalCommentKarma
	
	replyText += '---\n\n###Total score: ' + str(totalScore) + '\n\n###Recommended Gulag Sentence: '
	if totalScore > 0:
		sentenceLength = (totalScore + 1) ** 3
		if sentenceLength > 1000000000:
			replyText += 'Execution.'
		else:
			replyText += str(sentenceLength) + ' years.'
	else:
		replyText += '0 years.'
	replyText += '\n\n---\n\nI am a bot. Only the past 1,000 posts and comments are fetched.'
	
	return replyText

def handleRequest(request):#Handle a user's comment or private message requesting the bot to investigate a user's reactionariness.
	if not hasProcessed(request.id):
		userToInvestigate = extractUsername(request.body)
		if userToInvestigate != None:
			if userToInvestigate == 'isreactionarybot':#For smartasses.
				request.reply('Nice try.')
			elif not isValidUsername(userToInvestigate):
				request.reply('Invalid username.')
			else:
				request.reply( calculateReactionariness(userToInvestigate) )

def main():
	while True:
		usernameMentions = r.get_mentions()
		for mention in usernameMentions:
			handleRequest(mention)
		
		privateMessages = r.get_messages()
		for message in privateMessages:
			handleRequest(message)
		
		sleep(120)
	return 0

sqlConnection = sqlite3.connect(path + 'isReactionaryBot.db')
sqlCursor = sqlConnection.cursor()

r = praw.Reddit(user_agent='A program that checks if a user is a reactionary.')
r.login('isReactionaryBot', password)

sys.stderr = open(path + 'isReactionaryBotOutput.txt', 'w')

if __name__ == '__main__':
	main()
