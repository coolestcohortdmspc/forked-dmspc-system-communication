FROM postgres:18-alpine

WORKDIR /scripts

COPY load-staging-data.sh .

RUN chmod +x load-staging-data.sh

CMD ["./load-staging-data.sh"]