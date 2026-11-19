import argparse
from pathlib import Path
from .acquisition import acquire


def main():
    parser = argparse.ArgumentParser(description='ProcureIQ auditable data pipeline')
    parser.add_argument('--root', type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest='command', required=True)
    download = commands.add_parser('download')
    download.add_argument('--offline', action='store_true')
    commands.add_parser('investigate')
    db = commands.add_parser('db')
    database_commands = db.add_subparsers(dest='db_command', required=True)
    database_commands.add_parser('init')
    load_parser = database_commands.add_parser('load')
    load_parser.add_argument('--manifest', type=Path, help='Verified revision receipts; revisions load inactive')
    database_commands.add_parser('verify')
    activation = database_commands.add_parser('activate', help='Explicitly select a loaded source version')
    activation.add_argument('month')
    activation.add_argument('sha256')
    analytics = commands.add_parser('analytics')
    analytical_commands = analytics.add_subparsers(dest='analytics_command', required=True)
    for name in ('summary', 'verify', 'export'):
        command = analytical_commands.add_parser(name)
        command.add_argument('--start-month', help='Inclusive YYYY-MM')
        command.add_argument('--end-month', help='Inclusive YYYY-MM')
        command.add_argument('--expense-type')
        command.add_argument('--expense-area')
        command.add_argument('--entity')
        command.add_argument('--supplier-id', type=int)
        if name == 'export':
            command.add_argument('--output', type=Path)
    opportunities = commands.add_parser('opportunities')
    opportunity_commands = opportunities.add_subparsers(dest='opportunity_command', required=True)
    for name in ('detect', 'verify', 'export'):
        command = opportunity_commands.add_parser(name)
        command.add_argument('--start-month', help='Inclusive YYYY-MM')
        command.add_argument('--end-month', help='Inclusive YYYY-MM')
        command.add_argument('--expense-type')
        command.add_argument('--expense-area')
        command.add_argument('--entity')
        command.add_argument('--supplier-id', type=int)
        command.add_argument('--config', type=Path, help='JSON overrides for documented thresholds and weights')
        if name == 'export':
            command.add_argument('--output', type=Path)
    executive = commands.add_parser('executive')
    executive_commands = executive.add_subparsers(dest='executive_command', required=True)
    command = executive_commands.add_parser('export')
    command.add_argument('--scenario', type=Path, help='Validated scenario JSON matching the full reporting population or a category subset')
    command.add_argument('--output', type=Path, help='Local PPTX output path')
    app_db = commands.add_parser('app-db', help='Separate investigation application migrations')
    app_db.add_subparsers(dest='app_db_command',required=True).add_parser('init')
    args = parser.parse_args()
    if args.command == 'download':
        results = acquire(args.root, args.offline)
        for result in results:
            print(result['reporting_month'], result['status'], result.get('error', ''))
        if any(r['status'] == 'failed' for r in results):
            raise SystemExit(1)
    elif args.command == 'app-db':
        from .db import engine_from_env
        from .investigations.migrations import initialize_app
        engine=engine_from_env()
        try:
            initialize_app(engine,args.root)
            print('Application migrations verified/applied; analytical schema unchanged.')
        finally:
            engine.dispose()
    elif args.command == 'executive':
        import json
        from .db import engine_from_env
        from .ui.service import DashboardService
        from .executive import export_default
        engine = engine_from_env()
        try:
            result = export_default(DashboardService(engine), args.root, args.scenario, args.output)
            print(json.dumps(result, indent=2))
        finally:
            engine.dispose()
    elif args.command == 'opportunities':
        import json
        from .db import engine_from_env
        from .opportunities import run
        from .opportunity_model import load_config
        from .queries import FILTER_TYPES
        cfg = load_config(args.config)
        engine = engine_from_env()
        try:
            result = run(engine, args.root, args.opportunity_command,
                         {key: getattr(args, key) for key in FILTER_TYPES}, cfg, getattr(args, 'output', None))
            print(json.dumps(result, indent=2, default=str))
        finally:
            engine.dispose()
    elif args.command == 'analytics':
        import json
        from .db import engine_from_env
        from .analytics import run
        from .queries import FILTER_TYPES
        engine = engine_from_env()
        try:
            result = run(engine, args.root, args.analytics_command,
                         {key: getattr(args, key) for key in FILTER_TYPES}, getattr(args, 'output', None))
            print(json.dumps(result, indent=2, default=str))
        finally:
            engine.dispose()
    elif args.command == 'db':
        import json
        from .db import engine_from_env, initialize
        from .ingestion import load, activate
        from .reconciliation import verify
        engine = engine_from_env()
        try:
            if args.db_command == 'init':
                initialize(engine, args.root)
                print('Database migrations verified/applied.')
            elif args.db_command == 'load':
                print(json.dumps(load(engine, args.root, args.manifest), indent=2))
            elif args.db_command == 'verify':
                result = verify(engine, args.root)
                print(json.dumps(result, indent=2, default=str))
            else:
                activate(engine, args.root, args.month, args.sha256)
                print('Source version activated. Frozen-baseline verification requires the original versions.')
        finally:
            engine.dispose()
    else:
        from .profiling import investigate
        investigate(args.root)


if __name__ == '__main__':
    main()
