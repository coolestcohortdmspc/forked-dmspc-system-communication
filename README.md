# dmspc-system-communication
Code for prototyping system communication for the ngRadar project. This code is written by the Data Management & Software Prototyping Cohort (DMSPC).


# How to run locally:
__Please Note:__ This system does not work unless another trial of ExpeDat is obtained (either a free trial or purchased rights). If you do get access to the ExpeDat executables, an "expedat" directory will need to be added to the project root with all of the downloadable files inside of it.

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
For local dev, we spin up the following Docker containers, which you can see on a GUI using Docker Desktop:  

| Container Name | Description |
| :---: | :---: |
| kafka-node-1 | - |
| kafka-node-2 | - |
| kafka-node-3 | - |
| kafka-ui | GUI to see Kafka information (topics, messages, etc.) |
| seaweedfs | Object store for DDM images |
| dsoc-volume-init | Creates necessary Docker volumes |
| db_consumer | Kafka consumer to store all events in the database |
| kafka-init | Creates necessary Kafka topics |
| traefik_http | - |
| ngradar_website | The website |
| postgres | PostgreSQL database |
| expedat_server | Recipient of ExpeDat streamed data (servedat is installed and running here) |
| gbt | Green Bank Telescope simulator |
| vlba-sc | VLBA Site (St. Croix) |
| vlba-hn | VLBA Site (Hancock) |
| vlba-nl | VLBA Site (North Liberty) |
| vlba-fd | VLBA Site (Fort Davis) |
| vlba-la | VLBA Site (Los Alamos) |
| vlba-pt | VLBA Site (Pie Town) |
| vlba-kp | VLBA Site (Kitt Peak) |
| vlba-ov | VLBA Site (Owens Valley) |
| vlba-br | VLBA Site (Brewster) |
| vlba-mk | VLBA Site (Mauna Kea) |
| dsoc | DSOC (Domenici Socorro Operations Center) simulator |
| progress_tracker | Tracks ExpeDat stream progress to display on UI |
| portainer | A web-version of Docker Desktop |
| prometheus | Scrapes system metrics |
| grafana | Compiles and displays system metrics |
| tempo | - |
| otel-collector | - |
| postgres_exporter | - |
| kafka-exporter | - |
| k6 | - |