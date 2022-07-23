# Set Up a FastAPI Server

## Dev

Update `.env`

`docker-compose up -d`

Swagger docs: http://localhost:5000/docs

## Production

_(On an Ubuntu/Debian [basic droplet](https://bit.ly/BasicDroplet) or similar server.)_

Set up a [Traefik network](https://github.com/lfache/awesome-traefik/tree/master/traefik) with compose. 
Add the network name to `docker-compose.prod.yml`

`git clone {/fastapi/*}` or move files via deployment/sftp.

Rename/move the directory. Such as

`sudo cp -rlf /var/sftp/uploads/fastapi/. ~/api.example.com`

or 

`rsync -r -a /var/sftp/uploads/fastapi/. ~/api.example.com`

Change directories

`cd ~/api.example.com`

Update/overwrite `.env` settings

`sudo mv .env.prod .env`

Update `docker-compose.prod.yml` settings

Build and run the API with compose

`sudo docker-compose -f docker-compose.prod.yml up -d --build`