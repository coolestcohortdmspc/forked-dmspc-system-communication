import sys
import subprocess
import time


while True:
    result = subprocess.run(["lsof", sys.argv[1]], capture_output=True, text=True)
    output = result.stdout
    if output.strip():
        print("Output:\n", output)
    else:
        break

    time.sleep(1)

# TODO tell vlba it can start the etransfer!