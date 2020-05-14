FROM alpine:3.7
EXPOSE 3031
COPY . /app
WORKDIR /app
RUN apk add --no-cache \
	uwsgi-python3 \
	uwsgi-http \
        python3 \
	gcc \
	make \
	libffi-dev \
	python3-dev \
	musl-dev \
	libxml2-dev \
	libxslt-dev \
	openssl-dev

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

RUN apk del gcc \
	make

CMD [ "uwsgi", \
               "--ini", "uwsg.ini", \
               "--plugin", "http, python3", \
               "--http", ":3031", \
               "--wsgi-file", "server/pyrssw_wsgi.py" ]
