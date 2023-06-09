from dagster import Definitions, load_assets_from_modules

from . import all

all_assets = load_assets_from_modules([all])

defs = Definitions(
    assets=all_assets,
    jobs=[all.process_zip_file, all.process_csv_file],
    sensors=[all.check_for_zip_file, all.check_for_csv_file],
)
