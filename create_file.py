import uuid
import subprocess
import random
import os
from pathlib import Path


def main():
    file_name = f"{uuid.uuid4()}.bin"

    file_path = Path("raw_data") / file_name

    subprocess.run("pbcopy", text=True, input=file_name)

    file_mb = 10000

    file_size_bytes = file_mb * 1024 * 1024

    with open(file_path, "wb") as file:
        for _ in range(20):
            buffer = random.randbytes(int(file_size_bytes / 20))
            file.write(buffer)

    print(f"Successfully created a {file_mb}MB random binary file: {file_name}")


    # change name method
    # os.rename(file_path, "./raw_data/receiver_data_" + file_name)
    # print(f"Successfully created a {file_mb}MB random binary file: receiver_data_" + file_name)

main()