FROM alpine:latest

ENV CONFIG=/config/

RUN apk update && \
	apk upgrade && \
	apk add \
	py3-pip \
	tzdata \
	npm \
	git

RUN pip3 install \
	flask \
	requests \
	deep-translator \
	apscheduler

RUN rm -rf /var/cache/apk/*

COPY /app.py /app/app.py
COPY /templates /app/templates
COPY /static /app/static

ENTRYPOINT ["python3","-u","/app/app.py"]