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

So, the dagster new project docs don't tell us _anything_ about where to go
next.
I went on to read the [tutorial](https://docs.dagster.io/tutorial),
which you now do _not_ have to do :) .

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

## getting some assets

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

Play around with it, and then extend the code to:
