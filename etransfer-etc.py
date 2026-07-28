import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

"""
This script represents an e-transfer client (etc)
Requirement: This machine and the destination (daemon/etd) machine must have the jive e-transfer repo already cloned and built using the make command. 
The daemon must be ready to receive files by running ./etd --command tcp://:4004 --data udt://:8008
This script defines the directory you want to export from, and the directory you want to import into on the daemon.
"""

COMMAND_DIR = Path("/Users/tmatson/Documents/GitHub/etransfer/Darwin-arm64-native-opt/") #NOTE Replace with your etransfer path names
CLIENT_DIR = Path("/Users/tmatson/Documents/GitHub/etransfer/data/pickle5.jpeg") #NOTE Replace with your etransfer path names
#DAEMON_DIR = "/Users/ndepergola/Projects/etransfer-test/"
DAEMON_DIR = "/Users/tmatson/Documents/GitHub/etransfer/data-retrieved/"

is_valid_input = False

while not is_valid_input:
    # displays the current working source directory and asks for a path from there to source data
    current_source_folder = f"*/{os.environ.get('SOURCE_DIR').strip().split("/")[-2]}/"
    source_path = os.environ.get('SOURCE_DIR') + input(f"({current_source_folder})$ Enter your source file path: ")

    # displays the current working destination directory and asks for a path from there to transfer data to
    current_destination_folder = f"*/{os.environ.get('DESTINATION_DIR').strip().split("/")[-2]}/"
    destination_path = os.environ.get('DESTINATION_DIR') + input(f"({current_destination_folder})$ Enter your destination file path: ")

    print()
    print("Select a transfer mode, options are: ")
    print("--overwrite")
    print(" this restarts the file transfer. The remote file is truncated to zero size after which the whole source file is transferred.")
    print("--resume")
    print(" this resumes an operation. If the source file is longer than the destination file, the remaning bytes are transferred. If the source file's size is shorter or equal to the destination no bytes are transferred and no error is generated.")
    print()
    # asks for any optional modes, like --overwrite or --resume
    optional_mode = input("Enter a transfer mode or leave blank: ")

    if source_path[-1] == "/" or len(optional_mode.strip().split()) > 1:
        print()
        print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
        print("| Invalid input, please try again |")
        print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
        print()
    else:
        if destination_path[-1] != "/":
            destination_path = destination_path + "/"

        is_valid_input = True

if optional_mode.strip() == "":
    cmd = [
        "./etc", 
        Path(f"{os.environ.get('SOURCE_IP')}:{source_path}"), 
        f"{os.environ.get('DESTINATION_IP')}:{destination_path}"
    ]
else:
    option = optional_mode.strip().split()  # creates an array without whitespace from the input
    cmd = [
        "./etc", 
        Path(f"{os.environ.get('SOURCE_IP')}:{source_path}"), 
        f"{os.environ.get('DESTINATION_IP')}:{destination_path}"
    ] + option

result = subprocess.run(
    cmd,
    cwd=COMMAND_DIR,
    text=True,
    check=False,  # set True if you want exceptions on non-zero exit
)

if result.returncode != 0:
    print("Exit code:", result.returncode)
    raise RuntimeError("etransfer command failed")
