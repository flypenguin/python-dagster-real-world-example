import zlib
from random import randint

import pandas as pd
from dagster import (
    job,
    op,
    sensor,
    RunRequest,
    AssetMaterialization,
    asset_sensor,
    SensorEvaluationContext,
    EventLogEntry,
    AssetKey,
    RunConfig,
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
def find_relevant_items(context, files_list: list[str]):
    relevant_items = files_list[0 : len(files_list) // 2]
    for item in relevant_items:
        relevant_part = "/".join(item.split("/")[-2:])
        context.log_event(
            AssetMaterialization(
                asset_key="csv_file",
                metadata={
                    "s3_bucket": "a-bucket",
                    "s3_key": f"/second/path/{relevant_part}",
                },
            )
        )


@job
def process_zip_file():
    local_zip = download_zip_file()
    files_list = unpack_zip_file(local_zip)
    find_relevant_items(files_list)


@op
def load_csv_file(context) -> pd.DataFrame:
    location = context.op_config["s3_key"]
    return pd.DataFrame([[location]], columns=["location"])


@op
def handle_csv_file(df: pd.DataFrame) -> pd.DataFrame:
    apply_func = lambda x: zlib.crc32(x["location"].encode("utf-8"))
    tmp = df.apply(apply_func, axis=1)
    return pd.concat([df, tmp], axis=1)


@op
def save_csv_file(df: pd.DataFrame):
    print(df)


@job
def process_csv_file():
    save_csv_file(handle_csv_file(load_csv_file()))


@sensor(job=process_zip_file)
def check_for_zip_file():
    rstr = "".join([f"{randint(0, 9)}" for _ in range(6)])
    download_zip_file_config = {
        "config": {"s3_bucket": "a-bucket", "s3_key": f"/a/bucket/path/{rstr}"}
    }
    yield RunRequest(
        run_key=f"s3_file_{rstr}",
        run_config={"ops": {"download_zip_file": download_zip_file_config}},
    )


@asset_sensor(asset_key=AssetKey("csv_file"), job=process_csv_file)
def check_for_csv_file(context: SensorEvaluationContext, asset_event: EventLogEntry):
    # from here: https://is.gd/BocYt0
    # that _CANNOT_ be the way this is done?!?
    mat_metadata = asset_event.dagster_event.materialization.metadata
    load_csv_file_config = {"load_csv_file": {"s3_key": mat_metadata["s3_key"].value}}
    yield RunRequest(
        run_key=context.cursor, run_config=RunConfig(ops=load_csv_file_config)
    )
