ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8
COPY sucks /
RUN cd /sucks 

RUN apk add --no-cache python3 gcc build-base  && \
	python3 -m ensurepip --upgrade && \
	python3 setup.py install && \
	pip3 install paho-mqtt

RUN rm -rf /sucks
RUN apk del gcc build-base 
RUN rm -rf /root/.cache/pip

COPY vacuum.py /
WORKDIR /data

RUN chmod a+x /vacuum.py

# CMD [ "/vacuum.py" ]
CMD [ "/run.sh" ]
