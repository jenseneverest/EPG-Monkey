FROM alpine:latest

ENV CONFIG=/config/

RUN apk update && \
	apk upgrade && \
	apk add \
	py3-pip \
	tzdata \
	npm

RUN pip3 install \
	flask \
	requests \
	deep-translator \
	apscheduler

RUN rm -rf /var/cache/apk/*

COPY /app.py /app/app.py
COPY /templates /app/templates
COPY /static /app/static

RUN mkdir /app/tmp

ENTRYPOINT ["python3","-u","/app/app.py"]