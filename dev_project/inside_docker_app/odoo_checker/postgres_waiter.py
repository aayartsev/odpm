import socket
import time

from ...translations import _
from ..exceptions import PostgresError
from ...logging import get_module_logger

_logger = get_module_logger(__name__)

_MSG_STARTUP_TIMEOUT = _("PostgreSQL startup timeout exceeded")
_MSG_PORT_CHECK_ERROR = _("Error checking PostgreSQL port: {DETAIL}")
_MSG_VERIFY_TIMEOUT = _(
    "PostgreSQL credentials check timed out after {SECONDS}s for database {DBNAME}"
)
_MSG_MAX_ATTEMPTS = _("PostgreSQL credentials check failed after {ATTEMPTS} attempts")
_MSG_ROLE_MISSING = _("PostgreSQL role {USER} does not exist")
_MSG_AUTH_FAILED = _("PostgreSQL authentication failed for role {USER}")
_MSG_STILL_STARTING = _("PostgreSQL is still starting up")
_MSG_CONNECTION_FAILED = _("PostgreSQL connection failed: {DETAIL}")
_MSG_UNEXPECTED = _("Unexpected PostgreSQL connection error: {DETAIL}")
_MSG_PSYCOPG2_REQUIRED = _("psycopg2 is required.")


def _classify_operational_error(exc: Exception, *, user: str) -> str:
    text = str(exc).lower()
    if "role" in text and "does not exist" in text:
        return _MSG_ROLE_MISSING.format(USER=user)
    if "password authentication failed" in text:
        return _MSG_AUTH_FAILED.format(USER=user)
    if "starting up" in text or "connection refused" in text:
        return _MSG_STILL_STARTING
    return _MSG_CONNECTION_FAILED.format(DETAIL=str(exc))


def _is_transient_operational_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "starting up" in text or "connection refused" in text


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
            _logger.error(_MSG_PORT_CHECK_ERROR.format(DETAIL=e))
            return False

    def wait_for_postgres(self):
        """
        Main method for waiting for PostgreSQL to start
        """
        _logger.info(f"Waiting for PostgreSQL on {self.host}:{self.port}")

        while True:
            elapsed_time = time.time() - self.start_time
            if elapsed_time >= self.timeout:
                message = _MSG_STARTUP_TIMEOUT
                _logger.error(message)
                raise PostgresError(message)

            if self.is_postgres_up():
                _logger.info("PostgreSQL is up and running")
                break

            _logger.info(f"PostgreSQL is not available yet. Waiting {self.check_interval} seconds...")
            time.sleep(self.check_interval)

    def verify_postgres_credentials(
        self, dbname: str, user: str, password: str, *, max_attempts: int | None = None
    ) -> None:
        """Verify PostgreSQL credentials; retry transient startup errors."""
        try:
            import psycopg2
            from psycopg2 import OperationalError
        except ImportError as exc:
            message = _MSG_PSYCOPG2_REQUIRED
            _logger.error(message)
            raise PostgresError(message, exit_code=2) from exc

        start = time.time()
        attempt = 0

        while True:
            attempt += 1
            elapsed = time.time() - start

            if self.timeout and elapsed >= self.timeout:
                message = _MSG_VERIFY_TIMEOUT.format(
                    SECONDS=int(self.timeout),
                    DBNAME=dbname,
                )
                _logger.error(message)
                raise PostgresError(message)

            if max_attempts and attempt > max_attempts:
                message = _MSG_MAX_ATTEMPTS.format(ATTEMPTS=max_attempts)
                _logger.error(message)
                raise PostgresError(message)

            _logger.info(
                f"Attempt {attempt} | Elapsed: {elapsed:.1f}s | Checking '{dbname}'..."
            )

            try:
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
                return

            except OperationalError as exc:
                if _is_transient_operational_error(exc):
                    _logger.warning(f"Database not ready yet: {exc}")
                else:
                    message = _classify_operational_error(exc, user=user)
                    _logger.error(message)
                    raise PostgresError(message) from exc
            except Exception as exc:
                message = _MSG_UNEXPECTED.format(DETAIL=exc)
                _logger.error(message)
                raise PostgresError(message) from exc

            delay = min(self.check_interval * (1.2 ** (attempt - 1)), 30)
            _logger.info(f"Waiting {delay:.1f}s...")
            time.sleep(delay)

    def wait_for_postgres_db(self, dbname, user, password, max_attempts=None):
        """Backward-compatible alias for credential verification."""
        self.verify_postgres_credentials(
            dbname,
            user,
            password,
            max_attempts=max_attempts,
        )
