"""Manage task schedules."""
import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


@main.command("list")
@click.pass_obj
def list_tasks(obj):
    """List all scheduled tasks."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api, "list_scheduled_tasks", {}, "Fetching list of scheduled tasks"
    )


@main.command("add")
@click.option("--description", prompt="Description", required=True)
@click.option("--task-host", prompt="Task host", required=True)
@click.option("--task-token", prompt="Task token", required=True)
@click.option("--namespace", prompt="Namespace", required=True)
@click.option("--task", prompt="Task (function)", required=True)
@click.option("--params", prompt="Params (dict of args to function)", required=True)
@click.option(
    "--cron",
    prompt="Cron string (e.g. '*/5 * * * *' means every 5 mins)",
    required=True,
)
@click.option("--jitter", prompt="Jitter (int)", type=int, required=True)
@click.pass_obj
def add_task(
    obj, description, task_host, task_token, namespace, task, params, cron, jitter
):
    """Add new scheduled task."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "add_scheduled_task",
        dict(
            description=description,
            host=task_host,
            token=task_token,
            namespace=namespace,
            task=task,
            params=params,
            cron=cron,
            jitter=jitter,
        ),
        "Adding scheduled task",
    )


@main.command()
@click.argument("namespace")
@click.pass_obj
def remove_tasks_in_namespace(obj, namespace):
    """Remove all scheduled tasks in given namespace."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "remove_scheduled_tasks_in_namespace",
        dict(namespace=namespace),
        "Removing scheduled tasks",
    )


@main.command()
@click.argument("scheduled_task_id")
@click.pass_obj
def remove_task(obj, scheduled_task_id):
    """Remove scheduled task by id."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "remove_scheduled_task",
        dict(scheduled_task_id=scheduled_task_id),
        "Removing scheduled tasks",
    )
