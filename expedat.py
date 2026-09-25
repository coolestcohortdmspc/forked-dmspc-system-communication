import subprocess
import select
import os


def expedat_send(mvd_filepath):
    """
    Send one raw-data file from one local directory to another using expedat.

    movedat (mvd): sender
    servedat (svd): receiver

    """

    master_fd, slave_fd = os.openpty()

    svd_password = os.environ["SVD_PASSWORD"]
    svd_ip = os.environ["SVD_IP"]

    terminal_command = (
        f"./movedat {mvd_filepath} lcallahan:'{svd_password}'@{svd_ip}:/Users/lcallahan/DMSPC_GitHub/Expedat_Resources/"
    )

    process = subprocess.Popen(
        [
            terminal_command,
        ],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )

    os.close(slave_fd)

    buffer = ""

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

expedat_send("/Users/lcallahan/Documents/ngRadar/Debbie.png")