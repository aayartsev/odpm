# Миграция импортов 4.0→4.1

**С 4.1.0 root-shim модули в `dev_project/` удалены.** Старые импорты → `ModuleNotFoundError`.

| Удалённый импорт (shim 4.0) | Используйте |
|---|---|
| `dev_project.prepare_registry` | `dev_project.prepare` |
| `dev_project.plan_compose_preview` | `dev_project.plan.compose_preview` |
| `dev_project.plan_runtime_preview` | `dev_project.plan.runtime_preview` |
| `dev_project.plan_compose_runtime` | `dev_project.plan.compose_runtime` |
| `dev_project.plan_diff` | `dev_project.plan.diff` |
| `dev_project.plan_format` | `dev_project.plan.format` |
| `dev_project.plan_cli` | `dev_project.plan.cli` |
| `dev_project.compose_service_builder` | `dev_project.compose.service_builder` |
| `dev_project.compose_runtime` | `dev_project.compose.runtime` |
| `dev_project.compose_command_render` | `dev_project.compose.command_render` |
| `dev_project.start_command` | `dev_project.compose.start_command` |
| `dev_project.host_context` | `dev_project.host.context` |
| `dev_project.host_runtime` | `dev_project.host.runtime` |
| `dev_project.host_user_env` | `dev_project.host.user_env` |
| `dev_project.host_cli` | `dev_project.host.cli` |
| `dev_project.host_cli.args` | `dev_project.host.cli.args` |
| `dev_project.host_cli.parse_args` | `dev_project.host.cli.parse_args` |
| `dev_project.host_cli.params` | `dev_project.host.cli.params` |
| `dev_project.inside_docker_app.cli_params` | host: `dev_project.host.cli.params`; checker: `dev_project.inside_docker_app.params` |
| `dev_project.inside_docker_app.parse_args` | `dev_project.host.cli.parse_args` |
| `dev_project.project_env.compose` | `dev_project.compose.generator.ComposeGenerator` |

Checker CLI flags: `dev_project.inside_docker_app.params`.
