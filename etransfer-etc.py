import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

"""
This script represents an e-transfer client (etc)
Requirement: This machine and the destination (daemon/etd) machine must have the jive e-transfer repo already cloned and built using the make command. 
The daemon must be ready to receive files by running ./etd --command tcp://:4004 --data udt://:8008
This script defines the directory you want to export from, and the directory you want to import into on the daemon.
"""

COMMAND_DIR = Path("/Users/ndepergola/Projects/etransfer-test/etransfer/Darwin-arm64-native-opt/") #NOTE Replace with your etransfer path names
CLIENT_DIR = Path("/Users/ndepergola/Downloads/ReinerGamma.png")
#DAEMON_DIR = "/Users/ndepergola/Projects/etransfer-test/"
DAEMON_DIR = "/Users/tmatson/Documents/GitHub/etransfer/data-retrieved/"

cmd = ["./etc", f"{CLIENT_DIR}", f"{os.environ.get('TY_IP_ADDRESS')}:{DAEMON_DIR}"]

result = subprocess.run(
    cmd,
    cwd=COMMAND_DIR,
    capture_output=True,
    text=True,
    check=False,  # set True if you want exceptions on non-zero exit
)

print("Exit code:", result.returncode)
print("STDOUT:\n", result.stdout)
print("STDERR:\n", result.stderr)

if result.returncode != 0:
    raise RuntimeError("etransfer command failed")
