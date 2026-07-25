FROM chrislusf/seaweedfs:4.40

RUN apk add --no-cache gettext

COPY s3.json.template /s3.json.template
COPY filer.toml.template /filer.toml.template

COPY seaweedfs.sh /seaweedfs.sh
RUN chmod +x /seaweedfs.sh

# Expose ports: 9333 (Master), 8888 (Filer), 8333 (S3)
EXPOSE 9333 8888 8333

ENTRYPOINT ["/seaweedfs.sh"]

