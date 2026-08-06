import uuid
import random


def main():
    file_name = f"{uuid.uuid4()}.bin"

    file_mb = 10000

    file_size_bytes = file_mb * 1024 * 1024

    with open(file_name, "wb") as file:
        for _ in range(20):
            buffer = random.randbytes(int(file_size_bytes / 20))
            file.write(buffer)

    print(f"Successfully created a {file_mb}MB random binary file: {file_name}")

main()