import json

import click
import toml

from encapsia_cli import lib


@click.group("schedule")
def main():
    """Manage task schedules."""


@main.command("list")
@click.pass_obj
def list_tasks(obj):
    """List all scheduled tasks."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api, "list_scheduled_tasks", {}, "Fetching list of scheduled tasks"
    )


@main.command("add")
@click.option("--name", prompt="Name", required=False)
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
    obj, name, description, task_host, task_token, namespace, task, params, cron, jitter
):
    """Add new scheduled task."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "add_scheduled_task",
        dict(
            name=name,
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


@main.command()
@click.argument("namespace")
@click.argument("name")
@click.pass_obj
def remove_task_by_name(obj, namespace, name):
    """Remove scheduled task by namespace and name."""
    api = lib.get_api(**obj)
    schedules = lib.run_plugins_task(
        api, "list_scheduled_tasks", {}, "Fetching list of scheduled tasks"
    )
    for schedule in json.loads(schedules):
        if (schedule['namespace'] == namespace):
            if schedule['name'] == name:
                id = schedule['id']
                lib.run_plugins_task(
                    api,
                    "remove_scheduled_task",
                    dict(scheduled_task_id=id),
                    f"Removing scheduled task {schedule['name']} with {id}",
                )


@main.command()
@click.argument("namespace")
@click.argument("schedule-file")
def update_schedule(obj, namespace, schedule_file):
    """Update schedules for existing tasks.

    \b
    The schedule file must be toml with the following content:
    schedules = [
        {
            name = "<schedule to update>" # Required
            description = "<new description>" # Optional
            params = "<new params>" # Optional
            cron = "<new cron>" # Optional
        },
        ...
    ]
    """
    api = lib.get_api(**obj)
    with open(schedule_file) as f:
        _config = toml.load(f)
        replacement_schedules = _config['schedules']
    new_schedules = {
        s['name']: s for s in replacement_schedules
    }
    schedules = lib.run_plugins_task(
        api, "list_scheduled_tasks", {}, "Fetching tasks"
    )
    for schedule in json.loads(schedules):
        if (schedule['namespace'] == namespace):
            if schedule['name'] in new_schedules.keys():
                id = schedule['id']
                lib.run_plugins_task(
                    api,
                    "remove_scheduled_task",
                    dict(scheduled_task_id=id),
                    f"Removing {schedule['name']} with {id} from {namespace}",
                )
                new_schedule = new_schedules[schedule['name']]
                new_fields = {
                    k: v for k, v in new_schedule.items() if k in (
                        'description', 'params', 'cron'
                    )
                }
                schedule.update(new_fields)
                lib.run_plugins_task(
                    api,
                    "add_scheduled_task",
                    dict(
                        name=schedule['name'],
                        description=schedule['description'],
                        host=schedule['host'],
                        token=schedule['token'],
                        namespace=schedule['namespace'],
                        task=schedule['task'],
                        params=json.dumps(schedule['params']),
                        cron=schedule['cron'],
                        jitter=schedule['jitter'],
                    ),
                    f"Adding {schedule['name']}",
                )
