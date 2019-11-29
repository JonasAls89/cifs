FROM python:3-alpine

COPY ./validator.py /opt/service/
COPY ./service.py /opt/service/
COPY ./requirements.txt /opt/service/
WORKDIR /opt/service
RUN apk add --no-cache --virtual .build-deps gcc libc-dev libxslt-dev && \
    apk add --no-cache libxslt && \
    pip install --no-cache-dir lxml>=4.4.1 && \
    apk del .build-deps
RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["python3"]
CMD ["service.py"]