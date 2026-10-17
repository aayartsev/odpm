"""Normalize parsed odpm CLI args (4.8 compatibility layer)."""

from __future__ import annotations

from dataclasses import replace

from . import params
from .args import OdpmCliArgs


class CliNormalizeError(ValueError):
    """Incompatible or ambiguous legacy CLI combination."""


_HOST_TOOL_COMMANDS = frozenset(
    {
        params.PLAN_SUBCOMMAND,
        params.MANIFEST_SUBCOMMAND,
        params.MODULES_SUBCOMMAND,
        params.RUN_SUBCOMMAND,
    }
)


def _has_stack_db_flag(args: OdpmCliArgs) -> bool:
    return bool(
        args.db_backup is not None
        or args.db_restore
        or args.db_drop
        or args.get_dbs_list is not None
    )


def _stack_db_flag_count(args: OdpmCliArgs) -> int:
    count = 0
    if args.db_backup is not None:
        count += 1
    if args.db_restore:
        count += 1
    if args.db_drop:
        count += 1
    if args.get_dbs_list is not None:
        count += 1
    return count


def _has_module_extras(args: OdpmCliArgs) -> bool:
    return bool(
        args.i is not None
        or args.u is not None
        or args.set_admin_pass is not None
        or args.translate
        or args.sql_execute is not None
        or args.export_po_files
        or args.start_precommit
        or args.odoo_bin
        or args.test
        or args.screencasts
    )


def _legacy_prepare(args: OdpmCliArgs) -> bool:
    return bool(args.skip_start or args.update_lock or args.sync_manifest_locks)


def apply_stack_database_flags(args: OdpmCliArgs) -> OdpmCliArgs:
    """Map ``database backup|restore|drop|list`` onto legacy flag fields."""
    sub = args.database_subcommand
    if sub not in params.DATABASE_STACK_SUBCOMMANDS:
        return args
    if sub == params.DATABASE_LIST_SUBCOMMAND:
        return replace(args, get_dbs_list=args.get_dbs_list or "1")
    if sub == params.DATABASE_BACKUP_SUBCOMMAND:
        backup = True if args.db_backup is None else args.db_backup
        return replace(args, db_backup=backup)
    if sub == params.DATABASE_RESTORE_SUBCOMMAND:
        return args
    if sub == params.DATABASE_DROP_SUBCOMMAND:
        return replace(args, db_drop=True)
    return args


def normalize_cli_args(args: OdpmCliArgs) -> tuple[OdpmCliArgs, str | None]:
    """Return ``(normalized_args, deprecation_warning_or_none)``."""
    if args.command == params.DATABASE_SUBCOMMAND:
        if args.database_subcommand in params.DATABASE_STACK_SUBCOMMANDS:
            if _has_module_extras(args):
                raise CliNormalizeError(
                    'Module flags (-i/-u/…) are not allowed with '
                    f'"odpm database {args.database_subcommand}". '
                    'Use "odpm up --db-restore … -i …" for combined flows.'
                )
            return apply_stack_database_flags(args), None
        if args.database_subcommand in params.DATABASE_HOST_SUBCOMMANDS:
            if _has_module_extras(args) or _has_stack_db_flag(args):
                raise CliNormalizeError(
                    'Runtime/database flags are not allowed with '
                    f'"odpm database {args.database_subcommand}".'
                )
            return args, None
        return args, None

    if args.command in _HOST_TOOL_COMMANDS:
        if _has_module_extras(args) or _has_stack_db_flag(args):
            raise CliNormalizeError(
                f'Runtime/database flags are not allowed with "odpm {args.command}".'
            )
        return args, None

    if args.command is not None:
        if args.command == params.PREPARE_SUBCOMMAND:
            if _has_stack_db_flag(args):
                raise CliNormalizeError(
                    'Stack database flags cannot be combined with "odpm prepare".'
                )
            return replace(args, skip_start=True), None
        if args.command == params.BUILD_SUBCOMMAND:
            if _has_stack_db_flag(args):
                raise CliNormalizeError(
                    'Stack database flags cannot be combined with "odpm build".'
                )
            return replace(args, build_image=True), None
        if args.command == params.INIT_SUBCOMMAND:
            if _has_stack_db_flag(args):
                raise CliNormalizeError(
                    'Stack database flags cannot be combined with "odpm init".'
                )
            return args, None
        if args.command in {
            params.UP_SUBCOMMAND,
            params.SCAFFOLD_SUBPARSER_PARAM,
        }:
            return args, None
        return args, None

    # --- No explicit subcommand: legacy / bare path (4.8) ---
    if args.version:
        return args, None

    stack = _has_stack_db_flag(args)
    if (args.init or args.build_image or _legacy_prepare(args)) and stack:
        raise CliNormalizeError(
            "Cannot combine --init / --build-image / --skip-start "
            "(or lock flags) with --db-backup / --db-restore / --db-drop / --get-dbs-list."
        )

    if args.init:
        return (
            replace(args, command=params.INIT_SUBCOMMAND),
            'Legacy "--init" is deprecated; use "odpm init URL".',
        )

    if args.build_image:
        return (
            replace(args, command=params.BUILD_SUBCOMMAND, build_image=True),
            'Legacy "--build-image" is deprecated; use "odpm build".',
        )

    if _legacy_prepare(args):
        return (
            replace(args, command=params.PREPARE_SUBCOMMAND, skip_start=True),
            'Legacy prepare flags are deprecated; use "odpm prepare".',
        )

    if args.plan:
        return replace(args, command=params.PLAN_SUBCOMMAND), None

    stack_count = _stack_db_flag_count(args)
    extras = _has_module_extras(args)
    if stack_count == 1 and not extras:
        warning = (
            "Legacy root database flags are deprecated; "
            "use the matching \"odpm database …\" subcommand."
        )
        if args.get_dbs_list is not None:
            return (
                replace(
                    args,
                    command=params.DATABASE_SUBCOMMAND,
                    database_subcommand=params.DATABASE_LIST_SUBCOMMAND,
                    get_dbs_list=args.get_dbs_list or "1",
                ),
                warning,
            )
        if args.db_backup is not None:
            return (
                replace(
                    args,
                    command=params.DATABASE_SUBCOMMAND,
                    database_subcommand=params.DATABASE_BACKUP_SUBCOMMAND,
                ),
                warning,
            )
        if args.db_restore:
            return (
                replace(
                    args,
                    command=params.DATABASE_SUBCOMMAND,
                    database_subcommand=params.DATABASE_RESTORE_SUBCOMMAND,
                ),
                warning,
            )
        if args.db_drop:
            return (
                replace(
                    args,
                    command=params.DATABASE_SUBCOMMAND,
                    database_subcommand=params.DATABASE_DROP_SUBCOMMAND,
                    db_drop=True,
                ),
                warning,
            )

    bare_only = not (
        stack
        or extras
        or args.d
        or args.init
        or args.build_image
        or _legacy_prepare(args)
        or args.plan
    )
    if bare_only:
        warning = (
            'Bare "odpm" is deprecated; use "odpm up". '
            "In 5.0 bare odpm will print the subcommand help instead of starting the stack."
        )
    else:
        warning = 'Running without a subcommand is deprecated; use "odpm up …".'
    return replace(args, command=params.UP_SUBCOMMAND), warning
