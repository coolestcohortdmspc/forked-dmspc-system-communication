#!/usr/bin/env bash

set -euo pipefail

set -a
source .env
set +a

DSOC_DROPLET="root@${DSOC_DROPLET_IP}"
VLBA_DROPLET="root@${VLBA_DROPLET_IP}"
GBT_DROPLET="root@${GBT_DROPLET_IP}"

REMOTE_DIR="/root/${REMOTE_REPO}"

KAFKA_PROFILES="--profile kafka"
# KAFKA_SERVICES="zookeeper broker kafka-ui ngrok gbt seaweedfs dsoc ngrok-writer vlba"
# KAFKA_SERVICES="zookeeper kafka-broker kafka-ui kafka-init gbt seaweedfs dsoc vlba etr_daemon"

# the order of these services matter!! learned the hard way..
KAFKA_SERVICES="zookeeper kafka-broker kafka-init kafka-ui seaweedfs dsoc-volume-init"
SIM_SERVICES="etr_daemon gbt vlba dsoc"

COMMAND="$1"

case "$COMMAND" in

start)
    echo "Starting development environment..."
    docker compose up -d
    ;;

rebuild-old)
    echo "Rebuilding development environment..."
    # Take down kafka + sim containers
    docker compose stop $KAFKA_SERVICES
    docker compose rm -f $KAFKA_SERVICES
    docker compose stop $SIM_SERVICES
    docker compose rm -f $SIM_SERVICES
    # Take down the rest of the containers
    docker compose down
    # --no-cache ensures code changes are baked in cleanly
    docker compose build --no-cache
    # --force-recreate guarantees .env variable updates  and config updates are pushed into the container upon rebuild
    docker compose up -d --force-recreate
    # same with kafka profiles:
    docker compose $KAFKA_PROFILES up -d --force-recreate
    ;;

stop)
    echo "Stopping development environment..."
    docker compose down
    ;;

shell)
    docker compose exec ngradar_website bash
    ;;

logs)
    docker compose logs -f ngradar_website
    ;;

attach)
    docker attach ngradar_website_service
    ;;

load-staging-data)
    docker compose run --rm staging_loader
    ;;


kafka-up)
    echo "Starting Kafka infrastructure and storage..."
    docker compose $KAFKA_PROFILES up -d $KAFKA_SERVICES
    ;;

sims-up)
    echo "Starting simulator services..."
    docker compose $KAFKA_PROFILES up -d $SIM_SERVICES
    ;;

system-up)
    echo "Starting Kafka infrastructure and storage..."
    "$0" kafka-up
    echo "Starting simulator services..."
    "$0" sims-up
    ;;


kafka-down)
    echo "Stopping kafka infrastructure and storage..."
    docker compose stop $KAFKA_SERVICES
    docker compose rm -f $KAFKA_SERVICES
    ;;

sims-down)
    echo "Stopping simulator services..."
    docker compose stop $SIM_SERVICES
    docker compose rm -f $SIM_SERVICES
    ;;

system-down)
    echo "Stopping kafka infrastructure and storage..."
    docker compose stop $KAFKA_SERVICES
    docker compose rm -f $KAFKA_SERVICES
    echo "Stopping simulator services..."
    docker compose stop $SIM_SERVICES
    docker compose rm -f $SIM_SERVICES
    ;;

rebuild)
    ./control.sh system-down
    ./control.sh stop

    docker volume ls -q \
        | grep -v 'postgres_data$' \
        | xargs -r docker volume rm

    docker compose build --no-cache
    docker compose up -d --force-recreate

    ./control.sh system-up
    ;;

testcov)
    echo "Calculating unit test coverage..."
    pytest --cov=ngRadar_Website --cov-report=term-missing
    ;;

hard-reset)

    read -p "This will DELETE your local database and containers. Continue? (y/N): " ANSWER

    if [[ "$ANSWER" != "y" && "$ANSWER" != "Y" ]]; then
        exit 0
    fi

    docker compose down -v --remove-orphans

    docker system prune -f

    docker compose build --no-cache && docker compose up -d
    ;;

gbt-up)
    docker compose up -d gbt
    ;;

gbt-down)
    docker compose stop gbt
    docker compose rm -f gbt
    ;;

vlba-up)
    docker compose up -d vlba
    ;;

vlba-down)
    docker compose stop vlba
    docker compose rm -f vlba
    ;;

dsoc-up)
    "$0" start
    "$0" kafka-up
    docker compose up -d dsoc etr_daemon
    ;;

dsoc-down)
    docker compose stop dsoc etr_daemon
    docker compose rm -f dsoc etr_daemon
    "$0" kafka-down
    "$0" stop
    ;;

droplets-up)
    echo "Starting DSOC Droplet"
    ssh "$DSOC_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh start && ./control.sh system-up"
    
    echo "Starting VLBA Droplet"
    ssh "$VLBA_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh vlba-up"
    
    echo "Starting GBT Droplet"
    ssh "$GBT_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh gbt-up"
    ;;

droplets-down)
    echo "Stopping VLBA Droplet"
    ssh "$VLBA_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh vlba-down"
    
    echo "Stopping GBT Droplet"
    ssh "$GBT_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh gbt-down"
    
    echo "Stopping DSOC Droplet"
    ssh "$DSOC_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh system-down && ./control.sh stop"
    
    ;;
*)

    echo "Usage:"
    echo
    echo "./control.sh start"
    echo "./control.sh rebuild"
    echo "./control.sh kafka-up"
    echo "./control.sh kafka-down"
    echo "./control.sh stop"
    echo "./control.sh shell"
    echo "./control.sh logs"
    echo "./control.sh attach"
    echo "./control.sh load-staging-data"
    echo "./control.sh hard-reset"
    echo "./control.sh testcov"
    echo "./control.sh sims-up"
    echo "./control.sh sims-down"
    echo "./control.sh system-up"
    echo "./control.sh system-down"
    exit 1
    ;;

esac