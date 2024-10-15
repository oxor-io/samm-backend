# samm-backend

## Local
### Set up a virtual environment
python -m venv .venv
source .venv/bin/activate

### Install packages
pip install -r requirements.txt

### Launch dev server
fastapi dev samm_api/main.py


## Docker
### Bring down the old containers and volumes
docker-compose down -v

### Create the images and spin up the Docker containers
docker-compose up -d --build

### Try the API service
http://localhost:8004/docs