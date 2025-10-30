"""This file is used to test the prefect worker"""

from prefect import flow, task
from prefect.deployments import Deployment
from prefect.schedules import CronSchedule

@task
def say_hello(name: str = "World"):
    print(f"Hello, {name}!")

@flow(log_prints=True)
def my_flow(name: str = "World"):
    say_hello(name)

if __name__ == "__main__":
    my_flow.from_source(
        source="https://github.com/sfc-gh-jkang/e2e-flow.git",
        version="main",
        entrypoint="prefect/prefect_test.py:my_flow",
    ).deploy(
        name="my-test-flow",
        work_pool_name="google-vm",
        schedule=CronSchedule(cron="0 0 * * *"),
        flow=my_flow,
        tags=["test"],
        parameters={
            "name": "John",
        },
    )