# myapp/management/commands/ssh_tunnel.py
from sshtunnel import SSHTunnelForwarder

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Set up SSH tunnel for MySQL"

    def handle(self, *args, **kwargs):
        ssh_host = settings.SSH_HOST
        ssh_port = 22
        ssh_user = settings.SSH_USER
        ssh_key_file = settings.SSH_KEY
        remote_bind_address = ("localhost", 3306)
        self.stdout.write("Starting SSH tunnel...")

        try:
            tunnel = SSHTunnelForwarder(
                (ssh_host, ssh_port),
                ssh_username=ssh_user,
                ssh_pkey=ssh_key_file,
                remote_bind_address=remote_bind_address,
                local_bind_address=("127.0.0.1", 3307),  # Specify port 3307
            )

            tunnel.start()

            self.stdout.write(
                f"SSH tunnel started on local port {tunnel.local_bind_port}"
            )

            # Update Django settings to use the tunnel
            settings.DATABASES["secondary"]["PORT"] = tunnel.local_bind_port

            # Output the current database settings for debugging
            self.stdout.write(f"Current DATABASES settings: {settings.DATABASES}")

            # Test the connection to ensure it's working
            import MySQLdb

            try:
                conn = MySQLdb.connect(
                    host=settings.DATABASES["secondary"]["HOST"],
                    user=settings.DATABASES["secondary"]["USER"],
                    passwd=settings.DATABASES["secondary"]["PASSWORD"],
                    db=settings.DATABASES["secondary"]["NAME"],
                    port=tunnel.local_bind_port,
                )
                self.stdout.write("Successfully connected to the secondary database.")
                conn.close()
            except MySQLdb.Error as e:
                self.stderr.write(f"Error connecting to the database: {e}")

            # Keep the command running to keep the tunnel open
            try:
                self.stdout.write("SSH tunnel is active. Press Ctrl+C to stop.")
                while True:
                    pass
            except KeyboardInterrupt:
                self.stdout.write("Closing SSH tunnel...")
                tunnel.stop()
                self.stdout.write("SSH tunnel closed.")

        except Exception as e:
            self.stderr.write(f"Failed to start SSH tunnel: {e}")
            if hasattr(e, "args"):
                for arg in e.args:
                    self.stderr.write(f"Error detail: {arg}")
