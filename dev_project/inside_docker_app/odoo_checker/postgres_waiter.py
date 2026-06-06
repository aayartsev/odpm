import socket
import time

from ..exceptions import PostgresError
from ..logger import get_module_logger

_logger = get_module_logger(__name__)


class PostgresWaiter:
    def __init__(self, host='localhost', port=5432, timeout=60, check_interval=2):
        """
        Initialization of waiting parameters
        :param host: PostgreSQL server host
        :param port: PostgreSQL server port
        :param timeout: Maximum waiting time (seconds)
        :param check_interval: Check interval (seconds)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.check_interval = check_interval
        self.start_time = time.time()

    def is_postgres_up(self):
        """
        Check PostgreSQL server availability
        :return: True if server is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.check_interval)  # Timeout for connection attempt
                result = s.connect_ex((self.host, self.port))
                return result == 0
        except Exception as e:
            _logger.error(f"ОError checking port: {e}")
            return False

    def wait_for_postgres(self):
        """
        Main method for waiting for PostgreSQL to start
        """
        _logger.info(f"Waiting for PostgreSQL on {self.host}:{self.port}")
        
        while True:
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= self.timeout:
                message = "PostgreSQL startup timeout exceeded"
                _logger.error(message)
                raise PostgresError(message)
                
            if self.is_postgres_up():
                _logger.info("PostgreSQL is up and running")
                break
                
            _logger.info(f"PostgreSQL is not available yet. Waiting {self.check_interval} seconds...")
            time.sleep(self.check_interval)
    
    def wait_for_postgres_db(self, dbname, user, password, max_attempts=None):
        """Waits for a specific database to become available after a crash recovery."""
        try:
            import psycopg2
            from psycopg2 import OperationalError
        except ImportError as exc:
            message = "psycopg2 is required."
            _logger.error(message)
            raise PostgresError(message, exit_code=2) from exc

        start = time.time()
        attempt = 0
        
        while True:
            attempt += 1
            elapsed = time.time() - start

            if self.timeout and elapsed >= self.timeout:
                _logger.error(f"Timeout ({self.timeout}s). Database '{dbname}' did not recover.")
                return False

            if max_attempts and attempt > max_attempts:
                _logger.error(f"Maximum attempts reached ({max_attempts}).")
                return False

            _logger.info(f"Attempt {attempt} | Elapsed: {elapsed:.1f}s | Checking '{dbname}'...")

            try:
                # connect_timeout prevents hanging on network issues
                conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    dbname=dbname,
                    user=user,
                    password=password,
                    connect_timeout=5,
                )
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                conn.close()
                
                _logger.info(f"Database '{dbname}' is successfully available and ready.")
                return True

            except OperationalError as e:
                # During crash recovery, PostgreSQL returns:
                # "the database system is starting up" or "connection refused"
                _logger.warning(f"Database not ready yet: {e}")
            except Exception as e:
                _logger.error(f"Unexpected connection error: {e}")
                return False

            # Exponential backoff: interval → ... → max 30s
            delay = min(self.check_interval * (1.2 ** (attempt - 1)), 30)
            _logger.info(f"Waiting {delay:.1f}s...")
            time.sleep(delay)
