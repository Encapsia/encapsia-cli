"""Manage task schedules."""
import click

from encapsia_cli import lib


@click.group()
@click.option("--host", help="Name to use to lookup credentials in .encapsia/credentials.toml")
@click.option("--host-env-var", default="ENCAPSIA_HOST", help="Environment variable containing DNS hostname (default ENCAPSIA_HOST)")
@click.option(
    "--token-env-var",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
@click.pass_context
def main(host, host_env_var, token_env_var):
    """Manage task schedules."""
    host, token = lib.discover_credentials(host, host_env_var, token_env_var)
    ctx.obj = dict(host=host, token=token)


@main.command("list")
@click.pass_context
def list_tasks(ctx):
    """List all scheduled tasks."""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
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
@click.pass_context
def add_task(
    ctx,
    description,
    task_host,
    task_token,
    namespace,
    task,
    params,
    cron,
    jitter,
):
    """Add new scheduled task."""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
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
@click.pass_context
def remove_tasks_in_namespace(ctx, namespace):
    """Remove all scheduled tasks in given namespace."""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "remove_scheduled_tasks_in_namespace",
        dict(namespace=namespace),
        "Removing scheduled tasks",
    )


@main.command("remove")
@click.argument("scheduled_task_id")
@click.pass_context
def remove_task(ctx, scheduled_task_id):
    """Remove scheduled task by id."""
    lib.run_plugins_task(
        ctx.obj["host"],
        ctx.obj["token"],
        "remove_scheduled_task",
        dict(scheduled_task_id=scheduled_task_id),
        "Removing scheduled tasks",
    )
