# Set Up a FastAPI Server

Set up a [Traefik network](https://github.com/lfache/awesome-traefik/tree/master/traefik) with compose. 
Add the network name to  `docker-compose.prod.yml`

`git clone {/fastapi/*}` or move files via deployment/sftp/etc.

Rename/move the directory. Such as

`sudo cp -rlf /var/sftp/uploads/fastapi/. ~/api.example.com`

or 

`rsync -r -a /var/sftp/uploads/fastapi/. ~/api.example.com`

Change directories

`cd ~/api.example.com`

Update/overwrite `.env` settings

`sudo mv .env.prod .env` or `sudo nano .env` etc...

Update `docker-compose.prod.yml` settings

Build and run the API with compose

`sudo docker-compose -f docker-compose.prod.yml up -d --build`