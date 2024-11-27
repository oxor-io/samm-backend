# samm-backend

## Local
### Set up a virtual environment
```sh
$ python -m venv .venv
$ source .venv/bin/activate
```

### Install packages
```sh
$ pip install -r requirements.txt
```

### Launch dev server
```sh
$ cd samm-backend
$ python relayer/main.py
```

### Launch dev server
```sh
$ cd samm-backend
$ fastapi dev web/api/main.py
```

## Docker

### Fill the secrets in .env_web and .env_relayer by examples(.env_web.example and .env_relayer.example)
JWT_SECRET_KEY is a random number. You can get it by:
```sh
openssl rand -hex 32
```

### Bring down the old containers and volumes
```sh
$ docker-compose down -v
```

### Create the images and spin up the Docker containers
```sh
$ docker-compose up -d --build
```

### Try the API service
http://localhost:8004/docs