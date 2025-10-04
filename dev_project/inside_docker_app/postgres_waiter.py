import socket
import time
import logging
import sys

# Настройка логирования
from logger import get_module_logger
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
                _logger.error("PostgreSQL startup timeout exceeded")
                sys.exit(1)
                
            if self.is_postgres_up():
                _logger.info("PostgreSQL is up and running")
                break
                
            _logger.info(f"PostgreSQL is not available yet. Waiting {self.check_interval} seconds...")
            time.sleep(self.check_interval)