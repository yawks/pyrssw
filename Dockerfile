FROM alpine:latest
EXPOSE 3031
COPY . /app
WORKDIR /app
RUN apk add --no-cache \
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

RUN python3 -m venv /opt/venv
RUN . /opt/venv/bin/activate && pip install -r requirements.txt
#RUN pip install --no-cache-dir -r requirements.txt


CMD [ "/opt/venv/bin/python", \
        "-m", "main", "-c", "/config/config.ini"]