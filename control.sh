#!/usr/bin/env bash

set -euo pipefail

set -a
source .env
set +a

DSOC_DROPLET="root@${DSOC_DROPLET_IP}"
VLBA_1_DROPLET="root@${VLBA_DROPLET_IP}"  # TODO remove when scaling up
# TODO use these for scaling up AND ADD THESE IPs to .env
# VLBA_1_DROPLET="root@${VLBA_1_DROPLET_IP}"
# VLBA_2_DROPLET="root@${VLBA_2_DROPLET_IP}"
# VLBA_3_DROPLET="root@${VLBA_3_DROPLET_IP}"
GBT_DROPLET="root@${GBT_DROPLET_IP}"

REMOTE_DIR="/root/${REMOTE_REPO}"

KAFKA_PROFILES="--profile kafka"

# the order of these services matter!! learned the hard way..
KAFKA_SERVICES="zookeeper kafka-broker kafka-init kafka-ui seaweedfs dsoc-volume-init"
SIM_SERVICES="etr_daemon gbt vlba dsoc"

DIGITAL_OCEAN_SERVICES="portainer traefik"

# TODO add the commented vlba sims when scaling up! (vlba9 and vlba10 should start before gbt)
DSOC_SERVICES="ngradar_website postgres zookeeper kafka-broker kafka-init kafka-ui seaweedfs dsoc-volume-init dsoc etr_daemon"  # vlba7 vlba8
VLBA_1_SERVICES="vlba"  # vlba2
VLBA_2_SERVICES="vlba3 vlba4"
VLBA_3_SERVICES="vlba5 vlba6"
GBT_SERVICES="gbt"  # vlba9 vlba10

COMMAND="$1"

case "$COMMAND" in

start)
    echo "Starting development environment..."
    docker compose up -d
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

# Now that our live db lives in a DO droplet, I don't think we can run this command unless we want to ssh into the 
# dsoc droplet. but I don't think we use this command enough for it to matter since all the data in the live
# db is dummy data anyways. 
# load-staging-data)
#     docker compose run --rm staging_loader
#     ;;


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
    # Take down the rest of the containers
    docker compose down

    docker volume ls -q \
        | grep -v 'postgres_data$' \
        | xargs -r docker volume rm || true

    # --no-cache ensures code changes are baked in cleanly
    docker compose build --no-cache
    # --force-recreate guarantees .env variable updates  and config updates are pushed into the container upon rebuild
    docker compose up -d --force-recreate
    # same with kafka profiles:
    docker compose $KAFKA_PROFILES up -d --force-recreate
    docker compose up -d --force-recreate $SIM_SERVICES
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

digital-ocean-up)
    docker compose up -d $DIGITAL_OCEAN_SERVICES
    ;;

digital-ocean-down)
    docker compose stop $DIGITAL_OCEAN_SERVICES
    docker compose rm -f $DIGITAL_OCEAN_SERVICES
    ;;

gbt-up)
    docker compose up -d $GBT_SERVICES
    ;;

gbt-down)
    docker compose stop $GBT_SERVICES
    docker compose rm -f $GBT_SERVICES
    ;;

vlba-up)
    # TODO start all of these when scaling up!
    # Get the services that are passed as the argument to vlba-up
    SERVICES="${!2}"
    docker compose up -d $SERVICES
    ;;

vlba-down)
    # TODO remove all of these when scaling up!
    # Get the services that are passed as the argument to vlba-down
    SERVICES="${!2}"
    docker compose stop $SERVICES
    docker compose rm -f $SERVICES
    ;;

dsoc-up)
    docker compose up -d $DSOC_SERVICES
    ;;

dsoc-down)
    docker compose stop $DSOC_SERVICES
    docker compose rm -f $DSOC_SERVICES
    ;;

droplets-up)
    echo "Starting DSOC Droplet"
    ssh "$DSOC_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh dsoc-up"
    
    echo "Starting VLBA 1 Droplet"
    ssh "$VLBA_1_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh vlba-up VLBA_1_SERVICES"
    
    # TODO use these for scaling up
    # echo "Starting VLBA 2 Droplet"
    # ssh "$VLBA_2_DROPLET" \
    #     "cd $REMOTE_DIR && ./control.sh vlba-up VLBA_2_SERVICES"

    # echo "Starting VLBA 3 Droplet"
    # ssh "$VLBA_3_DROPLET" \
    #     "cd $REMOTE_DIR && ./control.sh vlba-up VLBA_3_SERVICES"
    
    echo "Starting GBT Droplet"
    ssh "$GBT_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh gbt-up"
    ;;

droplets-down)
    echo "Stopping GBT Droplet"
    ssh "$GBT_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh gbt-down"
    
    echo "Stopping VLBA 1 Droplet"
    ssh "$VLBA_1_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh vlba-down VLBA_1_SERVICES"
    
    # TODO use these for scaling up
    # echo "Stopping VLBA 2 Droplet"
    # ssh "$VLBA_2_DROPLET" \
    #     "cd $REMOTE_DIR && ./control.sh vlba-down VLBA_2_SERVICES"
    
    # echo "Stopping VLBA 3 Droplet"
    # ssh "$VLBA_3_DROPLET" \
    #     "cd $REMOTE_DIR && ./control.sh vlba-down VLBA_3_SERVICES"
    
    echo "Stopping DSOC Droplet"
    ssh "$DSOC_DROPLET" \
        "cd $REMOTE_DIR && ./control.sh dsoc-down"
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
    # echo "./control.sh load-staging-data"
    echo "./control.sh hard-reset"
    echo "./control.sh testcov"
    echo "./control.sh sims-up"
    echo "./control.sh sims-down"
    echo "./control.sh system-up"
    echo "./control.sh system-down"
    echo "./control.sh droplets-up"
    echo "./control.sh droplets-down"
    exit 1
    ;;

esac