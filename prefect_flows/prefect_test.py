"""This file is used to test the prefect worker"""

from prefect import flow, task

@task
def say_hello(name: str = "World"):
    print(f"Hello, {name}!")

@flow(log_prints=True)
def my_flow(name: str = "World"):
    say_hello(name)

if __name__ == "__main__":
    # Run the flow locally for testing
    my_flow()