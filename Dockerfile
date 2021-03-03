FROM alpine:3.13.1
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
        openssl-dev \
        py-pip \
        rust \
        cargo

#Required for Pillow
RUN apk --update add libxml2-dev libxslt-dev libffi-dev gcc musl-dev libgcc openssl-dev curl
RUN apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt

RUN apk del gcc \
        make

RUN set -x ; \
        addgroup -g 82 -S www-data ; \
        adduser -u 82 -D -S -G www-data www-data && exit 0 ; exit 1

CMD [ "uwsgi", \
        "--ini", "uwsg.ini", \
        "--plugin", "http, python3", \
        "--http", ":3031", \
        "--uid", "www-data", \
        "--gid", "www-data", \
        "--wsgi-file", "server/pyrssw_wsgi.py" ]
		