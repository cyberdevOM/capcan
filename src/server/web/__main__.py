from .app import app
from ..utils.deployer import write_bundle_settings


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Start the Capcan web server.')
    parser.add_argument('--demo', action='store_true', help='Enable demo mode (adds Demo settings tab)')
    args = parser.parse_args()

    if args.demo:
        app.config['DEMO_MODE'] = True
        write_bundle_settings(demo_mode=True)

    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host=host, port=port, debug=debug)


def stop():
    """Kill any process listening on the server port (default 5000)."""
    import os
    import re
    import signal
    import subprocess

    port = int(os.getenv('FLASK_PORT', 5000))

    # Try fuser first (most direct)
    result = subprocess.run(['fuser', f'{port}/tcp'], capture_output=True, text=True)
    pids = result.stdout.split()

    # Fallback: ss -tlnp
    if not pids:
        result = subprocess.run(['ss', '-tlnp', f'sport = :{port}'], capture_output=True, text=True)
        pids = re.findall(r'pid=(\d+)', result.stdout)

    if not pids:
        print(f'No process found on port {port}.')
        return

    for pid in pids:
        os.kill(int(pid), signal.SIGTERM)
        print(f'Stopped process {pid} (port {port}).')


if __name__ == '__main__':
    main()
