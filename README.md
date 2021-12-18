# SimpleDiscordDRM
A simple way to authorize apps via Discord roles

Creates a REST API with Flask that allows applications to check for certain roles given to a specific user. Useful for running beta tests within your Discord community.

## How it works
Given a session ID, the auth script will redirect to Discord's OAuth2 service where the user can choose to authorize your application. Once authorized, Discord redirects back to the script with an authorization token. From there the bot can read the user's roles and make a decision based on that data.

# Usage
All routes take a `sessionId` parameter, and responses are a JSON object with the following fields:  
`authorized: [1 or 0]` is the session authorized?  
`critical: [1 or 0]` does this request represent an error?  
`response: [string]` response text  
`sessionId` can be any identifier, such as a GUID. Max length of 256 

## Authenticating
From your application, open with the system's browser  
`/auth?sessionId={someSessionId}`  
   
Check the result with  
`/check?sessionId={someSessionId}` 
```
{
	"authorized": 0,
	"critical": 1,
	"response": "Member not in role."
}
```
```
{
	"authorized": 1,
	"critical": 0,
	"response": "<Discord username>"
}
```  
  
Cleanly end the session with  
`/end?sessionId={someSessionId}`  

# Running
Requires Python 3 with `pip`
Install dependencies  
`pip install flask`   
`pip install discord`  
  
Create your application and bot at https://discord.com/developers/applications  
Requires `SERVER MEMBERS INTENT` to be toggled on  
Add your app's `clientId`, `clientSecret`, `redirectUri` (all from OAuth2 tab), `botToken`, and `roleName` to `settings.py`  
  
Run
```
[export, set] FLASK_APP=auth
flask run
```

## Running with NGINX
Assumes using `gunicorn` and running the Flask app from `/home/auth`  

NGINX config:  
```
server {
	listen 443 ssl;
	server_name auth.someapp.com;

	location / {
		proxy_set_header Host $http_host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
		proxy_pass http://unix:/home/auth/auth.sock;
	}

	# SSL cert config
	...
}
```  

Run  
`gunicorn --bind unix:auth.sock -m 007 auth:app`
