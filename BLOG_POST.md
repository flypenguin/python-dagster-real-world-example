# Getting started with dagster

This is a longer one.

**Target audience: "Somewhat" experienced Pythonistas.**

I have an Airflow-shaped problem, but - techie that I am - I wanted to try
something new: **[Dagster](https://dagster.io)**.
It boldly claims is is "everything that Airflow can't be any more"
(paraphrased by me ;). So - yeah, sounds cool.

Unfortuntately, really, the docs suck quite a bit. It's a bit like what I call
the "Microsoft illness": there's _tons_ of docs, but somehow they are more
confusing than helpful.

So, let's define _my_ things to try:

- I want the process chain to be triggered by a queue
    - in my case, preferably AWS SQS
- I want to process a "thing", in that case a CSV file
    - during processing, that CSV file is split into smaller files which then
      should all be processed similarly
    - E.g. a ZIP file, which contains multiple CSV files, and also each CSV
      file could be split into several smaller based on a column value
    - The processing does not change, though.

That's a real-world requirement, which I think is kinda reasonable.

The overly easy
[Hello Dagster](https://docs.dagster.io/getting-started/hello-dagster)
really doesnt help here.
So, let's get started right "the right way (tm)".

I will follow the [tutorial](https://docs.dagster.io/tutorial), and start
using (almost) exactly their examples, so in the beginning you can
cross-reference if you want to.
I intend to diverse, though, to get my use cases done.

## Preparations - getting started

```bash
# set up a project with dagster, dagit and pandas as requirements first,
# i assume you know how to do this. then ...
dagster
dagster dev -m rwt

# "rwt" stands for "real world test"
# let's try if it works - this is already a deviation from the docs ...
dagster dev -m rwt
```

> **Side annoyance**: the reason `dagster dev` works is the `tool.dagster` entry i
> `pyproject.toml`.
> But how to specify more than one module (arrays for `module_name` don't
> work) is being said nowhere apparently).
> Or do you now have more than one module in a dagster project?

Before starting, you should have at least this directory structure now:

```text
.
├── pyproject.toml
├── requirements.txt
├── rwt
│   ├── __init__.py
│   └── assets.py           # we will start editing this one.
├── rwt_tests
│   ├── __init__.py
│   └── test_assets.py
└── setup.py
```

## Step 1 – getting some assets

After we're set up, let's
[get some assets](https://docs.dagster.io/tutorial/writing-your-first-asset#ingesting-data).

```python
# rwt/assets.py
import requests
from dagster import asset

@asset
def top_story_ids():
    newstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    return requests.get(newstories_url).json()[:100]
```

After you're done, you can execute `dagster dev` (if it's not running already)
and click "update" (bottom left corner) if you don't see anything. Then you
should see the assets.

Play around with it, and then extend the code to (immediately adding
[metadata](https://docs.dagster.io/tutorial/building-an-asset-graph#step-3-educating-users-with-metadata)
to the output):

```python
# new imports
import pandas as pd
from dagster import get_dagster_logger, Output, MetadataValue

# new asset
@asset
def top_stories(top_story_ids):
    logger = get_dagster_logger()
    results = []
    for item_id in top_story_ids:
        url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        item = requests.get(url).json()
        results.append(item)
    df = pd.DataFrame(results)
    logger.info(f"got {len(results)} top stories")
    return Output(
        value=df,
        metadata={
            "num_records": len(results),
            "preview": MetadataValue.md(df.head().to_markdown()),
        },
    )

```

**Noteworthy about the code changes:**

- The `top_stories` asset takes the asset `top_story_ids` as input.
  It's an asset created out of another asset.
- You can create a preview from and associate metadata to the output.
  (If you don't want that, simply `return df`)

## Step 2 - _thinking_ about splitting assets into multiples

### Introducing operations

Now, **the only thing we learned up to here are `Assets`.**
That's by far not enough.
Also, unfortunately, the docs present all that, but with little overview
about how it all fits together.

So, going back to the beginning: We want to _split assets into multiples_,
that are then processed independently.

Let me quote some docs here:

> "Asset" is Dagster's word for an entity, external to ops, that is mutated
> or created by an op. An asset might be a table in a database that an op
> appends to, an ML model in a model store that an op overwrites, or even a
> slack channel that an op writes messages to.
>
> Op outputs often correspond to assets. For example, an op might be
> responsible for recreating a table, and one of its outputs might be a
> dataframe containing the contents of that table.
>
> ([source](https://docs.dagster.io/concepts/ops-jobs-graphs/op-events))

> [...] it is possible to communicate with the Dagster framework either by
> yielding an event, logging an event, or raising an exception.
>
> ([source](https://docs.dagster.io/concepts/assets/asset-materializations))

> Jobs are the main unit of execution and monitoring in Dagster. The core of
> a job is a graph of ops connected via data dependencies.
>
> ([source](https://docs.dagster.io/concepts/ops-jobs-graphs/jobs))

> Asset sensors allow you to instigate runs when materializations occur.
>
> ([source](https://docs.dagster.io/concepts/partitions-schedules-sensors/asset-sensors))

That is everything but simple.

It seems we need to ...

- have an OP, which creates an asset, which represents our ZIP file
- have another series of OPs, that then work with this original asset,
  doing whatever we want them to do
- the whole thing probably needs to be wrapped in a
  [Job](https://docs.dagster.io/concepts/ops-jobs-graphs/jobs)

So, as an initial approach, we will **write a couple of OPs that do what we
want them to do, and try to trigger them somehow if we "find" a ZIP file.

### Dagster "Definitions"

What's that now?

Sorry, that interruption is necessary.

Before that worked all nice and well, because the `Definition` was correct.

What a "`Defition`" you ask?
Its a way of telling dagster which "things" you have, with "things" being
`Job`s, `Op`s, `Asset`s, and `Sensor`s. (We'll get to this later)

So, before you continue, have a look at that file: `rwt/__init__.py`, in which
there is the default `Definition`, that automatically loads our assets from
the example.

Naturally, we need to adjust that later.

## Step 3 - defining the ZIP workflow

Note: Everything in here is simulated, you don't need any AWS resources.

### The operations

Let's start with the operations first.
Let's have an **operation for each "step"**:

- **downloading a ZIP file** from an S3 bucket, returning the download location on disk
- **unpacking the ZIP file**, returning a files list
- **selecting some files** from that list, returning a smaller list of files

All of that is **wrapped into a `@job`**, that basically calls them one after another.
This is how that looks like:

```python
# i removed rwt/assets.py
# this file is now rwt/all.py

from random import randint

from dagster import (
    job,
    op,
    sensor,
    RunRequest,
)


@op
def download_zip_file(context) -> str:
    # LET'S TALK ABOUT CONTEXT SOON
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
```

So, this does not look too bad, right?

To test it, you have to adjust your `Definitions`:

```python
# file: rwt/__init__.py
from dagster import Definitions, load_assets_from_modules

from . import all

all_assets = load_assets_from_modules([all])

defs = Definitions(
    assets=all_assets,
    jobs=[all.process_zip_file],
)
```

Now, if you reload your code in dagster now, it should show all that.
