"""Manage task schedules."""
import click

from encapsia_cli import lib


@click.group()
def main():
    """Manage task schedules."""


@main.command("list")
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def list_tasks(host, token):
    """List all scheduled tasks."""
    lib.run_plugins_task(
        host,
        lib.get_env_var(token),
        "list_scheduled_tasks",
        {},
        "Fetching list of scheduled tasks",
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
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def add_task(
    description,
    task_host,
    task_token,
    namespace,
    task,
    params,
    cron,
    jitter,
    host,
    token,
):
    """Add new scheduled task."""
    lib.run_plugins_task(
        host,
        lib.get_env_var(token),
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


@main.command("remove_in_namespace")
@click.argument("namespace")
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def remove_tasks_in_namespace(namespace, host, token):
    """Remove all scheduled tasks in given namespace."""
    lib.run_plugins_task(
        host,
        lib.get_env_var(token),
        "remove_scheduled_tasks_in_namespace",
        dict(namespace=namespace),
        "Removing scheduled tasks",
    )


@main.command("remove")
@click.argument("scheduled_task_id")
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def remove_task(scheduled_task_id, host, token):
    """Remove scheduled task by id."""
    lib.run_plugins_task(
        host,
        lib.get_env_var(token),
        "remove_scheduled_task",
        dict(scheduled_task_id=scheduled_task_id),
        "Removing scheduled tasks",
    )
