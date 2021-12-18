from settings import Settings
from flask import Flask, request, redirect
import requests
import discord
from discord.utils import get
import threading
import json

class Oauth(object):
	clientId = Settings.clientId
	clientSecret = Settings.clientSecret
	scope = "identify"
	redirectUri = Settings.redirectUri
	discordApiUrl = "https://discordapp.com/api"
	discordLoginUrl = "{}/oauth2/authorize?client_id={}&redirect_uri={}&response_type=code&scope={}".format(discordApiUrl, clientId, redirectUri, scope)

class ServiceResponse(object):
	def __init__(self, authorized, critical, response):
		self.authorized = authorized
		self.critical = critical
		self.response = response

	def toJson(self):
		return json.dumps(self.__dict__)

class DiscordBot(discord.Client):
	container = None
	isReady = False

	async def on_ready(self):
		self.isReady = True
		print('Logged in as', self.user)
		self.loop.create_task(self.container.updateBotStatus())

class AuthApp(Flask):
	bot = DiscordBot()
	sessionIds = { }
	activeSessions = [ ]
	nicknames = { }

	async def startBot(self):
		await self.bot.start(Settings.botToken)

	async def updateBotStatus(self):
		if self.bot.isReady:
			count = len(self.activeSessions)
			what = "tester" if count == 1 else "testers"
			await self.bot.change_presence(activity = discord.Activity(type = discord.ActivityType.watching, name = "{} {} test".format(count, what)))

	def __init__(self, name = None):
		self.bot.container = self
		self.bot.loop.create_task(self.startBot())
		thread = threading.Thread(target = self.bot.loop.run_forever, args = ())
		thread.daemon = True
		thread.start()

		super(AuthApp, self).__init__(name)

app = AuthApp(__name__)

@app.route("/auth", methods = ["get"])
def auth():
	if (not app.bot.isReady):
		return ServiceResponse(0, 1, "Discord bot not logged in.").toJson()
	sessionId = request.args.get("sessionId")[0:256]
	if (sessionId == None):
		return ServiceResponse(0, 1, "Invalid session ID.").toJson()
	resp = app.make_response(redirect(Oauth.discordLoginUrl))
	resp.set_cookie("sessionId", value = sessionId)
	return resp

@app.route("/", methods = ["get"])
def index():
	if (not app.bot.isReady):
		return ServiceResponse(0, 1, "Discord bot not logged in.").toJson()
	sessionId = request.cookies.get("sessionId")[0:256]
	if (sessionId == None):
		return ServiceResponse(0, 1, "Invalid session ID.").toJson()
	code = request.args.get("code")
	if (code == None):
		return ServiceResponse(0, 1, "Invalid request.").toJson()
	app.sessionIds[sessionId] = code 
	#print("{} -> {}".format(sessionId, code))
	return "You may now close this page."

@app.route("/check", methods = ["get"])
def check():
	if (not app.bot.isReady):
		return ServiceResponse(0, 1, "Discord bot not logged in.").toJson()
	sessionId = request.args.get("sessionId")[0:256]
	if (sessionId in app.activeSessions):
		return ServiceResponse(1, 0, app.nicknames[sessionId]).toJson()
	if (sessionId == None):
		return ServiceResponse(0, 0, "Invalid session ID.").toJson()
	if (sessionId not in app.sessionIds):
		return ServiceResponse(0, 0, "User not logged in.").toJson()
	code = app.sessionIds.pop(sessionId)
	headers = {
		"Content-Type": "application/x-www-form-urlencoded"
	}
	data = {
		"client_id": Oauth.clientId,
		"client_secret": Oauth.clientSecret,
		"grant_type": "authorization_code",
		"code": code,
		"redirect_uri": Oauth.redirectUri,
		"scope": Oauth.scope
	}
	response = requests.post(url = "{}/oauth2/token".format(Oauth.discordApiUrl), data = data, headers = headers)
	token = response.json()["access_token"]
	headers = {
		"Authorization": "Bearer {}".format(token)
	}
	response = requests.get(url = "{}/users/@me".format(Oauth.discordApiUrl), headers = headers)
	user = response.json()
	member = get(app.bot.get_all_members(), id = int(user["id"]))
	if (member == None):
		return ServiceResponse(0, 1, "Member not found.").toJson()
	if (get(member.roles, name = Settings.roleName) == None):
		return ServiceResponse(0, 1, "Member not in role.").toJson()

	if (sessionId not in app.activeSessions):
		app.activeSessions.append(sessionId)
	app.bot.loop.create_task(app.updateBotStatus())

	app.nicknames[sessionId] = user["username"]
	return ServiceResponse(1, 0, app.nicknames[sessionId]).toJson()

@app.route("/end", methods = ["get"])
def end():
	if (not app.bot.isReady):
		return ServiceResponse(0, 1, "Discord bot not logged in.").toJson()
	sessionId = request.args.get("sessionId")[0:256]
	if (sessionId == None or sessionId not in app.activeSessions):
		return ServiceResponse(0, 0, "Invalid session ID.").toJson()
	app.activeSessions.remove(sessionId)
	app.nicknames.remove(sessionId)
	app.bot.loop.create_task(app.updateBotStatus())
	return ServiceResponse(1, 0, "Goodbye.").toJson()

if __name__ == "__main__":
	app.run(debug = False, use_reloader = False, host = "0.0.0.0")