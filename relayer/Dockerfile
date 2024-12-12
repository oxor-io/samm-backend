# pull official base image
FROM python:3.12.7-alpine3.20

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apk update \
  && apk add gcc nodejs npm curl libc++-dev libc6-compat jq \
  && apk cache clean

# download and execute bbup
# RUN curl -L bbup.dev | ash
# RUN bbup -v 0.57.0
RUN curl -L https://raw.githubusercontent.com/AztecProtocol/aztec-packages/refs/heads/master/barretenberg/bbup/install | ash
RUN ash /root/.bb/bbup -v 0.57.0
RUN ln -s /root/.bb/bb /usr/local/bin/bb

# install npm dependencies
COPY ./package.json .
COPY ./package-lock.json .
RUN npm install

# install python dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# touch proof
RUN touch ./target/proof

# add app
COPY . .
