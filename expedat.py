import subprocess
import select
import os
from dotenv import load_dotenv

load_dotenv()


def expedat_send(mvd_filepath):
    """
    Send one raw-data file from one local directory to another using expedat.

    movedat (mvd): sender
    servedat (svd): receiver

    """

    master_fd, slave_fd = os.openpty()

    svd_password = os.environ["SVD_PASSWORD"]
    svd_ip = os.environ["SVD_IP"]
    svd_user = os.environ["SVD_USER"]
    recipient_directory = os.environ["RECIPIENT_DIR"]

    terminal_command = [
        "./movedat",
        mvd_filepath,
        f"{svd_user}:{svd_password}@{svd_ip}:{recipient_directory}",
    ]

    #location where movedat is saved on my computer:
    mvd_location = os.environ["MVD_LOC"]

    process = subprocess.Popen(
        terminal_command,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        cwd=mvd_location
    )

    os.close(slave_fd)

    try:
        while process.poll() is None:
            readable, _, _ = select.select(
                [master_fd],
                [],
                [],
                0.5,
            )

            if not readable:
                continue

            try:

                terminal_output = os.read(master_fd, 4096).decode(
                    "utf-8",
                    errors="replace",
                )

            except OSError:
                break

            # Print the actual etc output to Docker logs.
            print(terminal_output, end="", flush=True)

    finally:
        os.close(master_fd)

    return_code = process.wait()

    if return_code != 0:
        raise subprocess.CalledProcessError(
            return_code,
            process.args,
        )

mvd_filepath = os.environ["MVD_FILEPATH"]
expedat_send(mvd_filepath)