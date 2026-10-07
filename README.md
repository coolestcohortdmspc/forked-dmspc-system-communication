# dmspc-system-communication
Code for prototyping system communication for the ngRadar project. This code is written by the Data Management & Software Prototyping Cohort (DMSPC).


# How to run locally:
| File | Purpose |
| :---: | :---: |
| `Dockerfile` | Builds the app image: installs Python deps, collects Django static files, runs the dev server |
| `Docker-compose.yml file.` | Orchestrates the app container + a Postgres container on a shared network |
| `load_staging_data.Dockerfile` | A separate, one-off image used only to dump/load staging data from our demo db to the local DB (for local development only) |
| `control.sh` | A thin wrapper script so the team doesn't need to memorize `docker compose` invocations |
| `.env` | Environment variables consumed by `/settings.py` (our .env file is never committed to Github - please ask team for the .env file for local dev) |

# Create a Virtual Environment
`$python3 -m venv .venv`

# Start the Virtual Environment
`$source .venv/bin/activate`


## For your convenience, use the below `control.sh` wrapper controls:

`control.sh` wraps common operations.
The commands below are the most useful to start up this system locally. Please see the control.sh file for the full list of additional commands. Run these commands in your terminal to accomplish any of the following:
```
./control.sh system-up      # This is all you need to start up the entire system. Starts 
                            # the Kafka (kafka-up), website/database (start) and sim 
                            # (sims-up) services.
                            # This command initiates each Docker container in a specific 
                            # order to prevent race conditions.

./control.sh rebuild        # Requires an input after rebuild; takes a container name to
                            # specify which container to rebuild. Can give multiple inputs
                            # separated by a single space.

./control.sh rebuild-all    # Rebuilds all containers. Performs a system-down, deletes all
                            # Docker volumes, rebuilds all services, and initiates all 
                            # containers.

./control.sh hard-reset     # (destructive) Clears database, removes caching, and force 
                            # recreates all containers.

./control.sh system-down    # Stops all system containers.

./control.sh shell          # Brings the user to the website container shell, allowing 
                            # the user to run commands inside.

./control.sh testcov        # Calculates unit test coverage and prints the test results in 
                            # the terminal.

./control.sh refresh        # Force recreates all containers, retaining cache and Docker
                            # images.
```
# Commands Within the Control Shell
`$python3 manage.py migrate`            # Retrieves the latest database migrations and 
                                        # applies them.

`$python3 manage.py makemigrations`     # Creates new database changes.

`$python3 manage.py createsuperuser`    # Allows for a new website user to be created 
                                        # after hard reset or database deletion.


## Summary of Containers:
For local dev, we have the following services spun up in local Docker containers, which you can see on a GUI using Docker Desktop:  
- Our website that you can visit via localhost in your preferred browser.  
- A local postgreSQL database that you can connect to using DBeaver.  
- When you do a ./control.sh system-up you start the following:     
    1. Kafka services:   
            - ZooKeeper  
            - Kafka broker  
            - Kafka UI  
            - Kafka topic initialization
            - SeaweedFS  
    2. Sim services:  
            - E-Transfer daemon  
            - GBT sim  
            - VLBA sim  
            - DSOC sim 

