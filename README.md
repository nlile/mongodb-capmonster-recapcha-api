# Self-Hosted CapMonster Cloud API
Send requests to a single [CapMonster](https://bit.ly/CapMonster2) instance from scripts/programs 
on workstations/servers that do not belong to the same LAN.

ZennoLab's CapMonster is a Windows software package for recognizing captchas and is a self-hosted alternative to
CapMonster.cloud

_Please be aware that the CapMonster TOS states you "may only use the software for personal purposes."_

## Project Structure

### capmonster/local/*
`Server.py` runs alongside a single license of [ZennoLab's CapMonster 2](https://bit.ly/CapMonster2). The `client.py`
has examples of submitting jobs directly to the DB or API.
If you're integrating this into your own applications and trust every `client.py` with DB rw privileges, fastapi is not necessary. 
However, integration into 3rd party apps will be difficult/impossible without an API endpoint.

### capmonster/fastapi/*
Allows clients to make requests to a custom domain (FastAPI endpoints) that handles ReCaptcha job requests. 
Includes endpoints that mimic 2Captcha's API as well as verbose pydantic (JSON) response models.
`/local/server.py` feeds queue items to a single instance of CapMonster 2.

Unlike `/local/client.py`, client requests do not need DB rw access. 
In other words, clients make requests to a custom domain/FastAPI endpoints versus submitting jobs directly into the DB.

## Getting started

### Requirements:
- Create a "Free & Hobby Cluster" with [MongoDB Atlas](https://bit.ly/MongoDBCloud)
- License of [ZennoLab's CapMonster 2](https://bit.ly/CapMonster2)
  - Windows machine to run CapMonster
- [DigitalOcean Basic Droplet](https://bit.ly/BasicDroplet) or other server instance & domain

### Setup & Installation
**/local**
- Running instance of CapMonster with Recaptcha2 Sitekey Addon (paid license)
- Clone the full repo (Depends on schema from `capmonster/fastapi/app/schema`)
- Install requirements `pip install -r requirements.txt`
- `mv .env.example .env` and update settings
- `python3 ./server.py`

#### Usage
`server.py` must be running on the same PC as CapMonster. It listens for new jobs, submits them to CapMonster via `captcha_solver.py`, and updates the DB with results. `captcha_solver.py` uses the 2CaptchaAPI to communicate with CapMonster. 

`client.py` is a simple implementation example. `client.py` can run anywhere so long as it has r/w access to the MongoDB collection `server.py` monitors.

**/fastapi**
- Install docker & docker-compose on a server, such as [DigitalOcean's Basic Droplet](https://bit.ly/BasicDroplet). Docker with developer tools is also available as a DigitalOcean 1-Click Applications.
- Copy the repo & follow instructions in [/fastapi/README.md](/fastapi/README.md)

#### Usage
Replace any 2Captcha API calls with FastAPI endpoints. 
Or, intercept applications making 2Captcha requests by editing the machine's host file.

## Purging garbage

Purge garbage (old ReCaptcha jobs) in the DB after any minute interval using the `remove_garbage` flag locally in 
`server` or with the FastAPI endpoint `/api/v1/garbage`.

## References

- [ZennoLab CapMonster Wiki](https://zennolab.com/wiki/en:addons:capmonster:work-with-other)
- [Buy CapMonster 2](https://bit.ly/CapMonster2)
- [2Captcha API](https://2captcha.com/2captcha-api)

## TODO

- ~~Testing~~
- ~~Prod submit job function for client.py~~
- Optimize MDB connections/instances
- ~~FastAPI interface~~
  - ~~Pydantic models already in use~~ ~~(schema.py)~~
  - Multiple Authentication/keys/users
- ~~Proxy username/pass~~
- Pull from pool of rotating proxies if no proxy submitted
- 