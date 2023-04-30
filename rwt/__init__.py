from dagster import Definitions, load_assets_from_modules

from . import all

all_assets = load_assets_from_modules([all])

defs = Definitions(
    assets=all_assets,
    jobs=[all.process_zip_file],
)
