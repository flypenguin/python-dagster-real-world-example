from random import randint

from dagster import (
    job,
    op,
    sensor,
    RunRequest,
)


@op
def download_zip_file(context) -> str:
    # in "context" will be the information where to download the file
    # this was done in the sensor.
    zip_file_url = context.op_config["s3_key"].split("/")[-1]
    return f"/some/static/location/{zip_file_url}"


@op
def unpack_zip_file(local_zip) -> list[str]:
    local_files = [f"{local_zip}/{i}" for i in range(10)]
    return local_files


@op
def find_relevant_items(files_list: list[str]) -> list[str]:
    return files_list[0 : len(files_list) // 2]


@job
def process_zip_file():
    local_zip = download_zip_file()
    files_list = unpack_zip_file(local_zip)
    find_relevant_items(files_list)
