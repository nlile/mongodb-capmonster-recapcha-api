# Self-Hosted CapMonster Cloud API
Send requests to a single CapMonster instance from scripts/programs that do not belong to the same LAN.

### capmonster/local/*
Runs alongside a single license of ZennoLab's CapMonster 2. 

### capmonster/fastapi/app/*
Send ReCaptcha jobs to FastAPI endpoints from anywhere without granting DB rw access.

Optional feature. Allows clients to make requests to a custom domain/FastAPI endpoints versus submitting jobs directly into the DB.

Includes endpoints that mimic 2Captcha's API as well as verbose pydantic (JSON) response models.

## Setup & Requirements:
- Create a "Free & Hobby Cluster" with [MongoDB Atlas](https://cloud.mongodb.com/) (free)

**/fastapi**
- Install docker & docker-compose on a server, such as [DigitalOcean's Basic Droplet](https://www.digitalocean.com/products/droplets/).
- Copy the repo & follow instructions in `/fastapi/README.md`

**/local**
- Running instance of CapMonster with Recaptcha2 Sitekey Addon (paid license)
- Clone the full repo (Depends on schema from `capmonster/fastapi/app/schema`)
- Install requirements `pip install -r requirements.txt`
- `mv .env.example .env` and update settings
- `python ./server.py`

`server.py` must be running on the same PC as CapMonster. It listens for new jobs, submits them to CapMonster via `captcha_solver.py`, and updates the DB with results. `captcha_solver.py` uses the 2CaptchaAPI to communicate with CapMonster. 

`client.py` is a simple implementation example. `client.py` can run anywhere so long as it has r/w access to the MongoDB collection `server.py` monitors.

## Purging garbage



## References

- [ZennoLab CapMonster Wiki](https://zennolab.com/wiki/en:addons:capmonster:work-with-other)
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