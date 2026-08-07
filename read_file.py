import sys
import subprocess
import time
from pathlib import Path


# lsof method
while True:
    result = subprocess.run(["lsof", sys.argv[1]], capture_output=True, text=True)
    output = result.stdout
    if output.strip():
        print("Output:\n", output)
    else:
        break

    time.sleep(1)

# TODO tell vlba it can start the etransfer!


# name change method

# check for files with certain naming structure, i.e. receiver_data_uuid.bin
# cur_list = list(Path("./raw_data").glob('receiver_data_*'))
# cur_size = len(cur_list)
# while True:
#     new_size = len(list(Path("./raw_data").glob('receiver_data_*')))
#     if new_size > cur_size:
#         new_list = list(Path("./raw_data").glob('receiver_data_*'))
#         new_file = list(set(new_list) - set(cur_list))[0]
#         print(f"{new_file} is ready for etransfer!")
#         cur_list.append(new_file)
#         cur_size = new_size
#     else:
#         print("No new files...")

#     time.sleep(1)

# if the number of files increases, tell vlba to start the etransfer