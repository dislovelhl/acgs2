
import logging

logger = logging.getLogger(__name__)

from pathlib import Path
from datetime import datetime
from typing import Dict
"""
List, Optional, Union, Any, Tuple
"""

"""
ACGS Code Analysis Engine - Database Manager
PostgreSQL connection management with constitutional compliance.
"""

Constitutional Hash: cdd01ef066bc6cf2


from contextlib import asynccontextmanager
from typing import Any

import asyncpg
from app.utils.constitutional import (
    CONSTITUTIONAL_HASH,
    ensure_constitutional_compliance,
)
from app.utils.logging import get_logger
from asyncpg import Pool

logger = get_logger("config.database")


class DatabaseManager:
    
    Database manager for ACGS Code Analysis Engine with constitutional compliance.
    

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        database: str = "acgs_code_analysis",
        username: str = "acgs_user",
        password: str = "",
        min_connections: int = 5,
        max_connections: int = 20,
        command_timeout: float = 60.0,
    ):
        
        Initialize database manager.

        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Database username
            password: os.environ.get("DATABASE_URL", os.environ.get("DEFAULT_VALUE", "fallback"))
            min_connections: Minimum connections in pool
            max_connections: Maximum connections in pool
            command_timeout: Command timeout in seconds
        
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = os.environ.get("DATABASE_URL", os.environ.get("DEFAULT_VALUE", "fallback"))
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.command_timeout = command_timeout

        # Connection pool
        self.pool: Pool | None = None
        self.is_connected = False

        logger.info("Database manager initialized",
            extra={
                "host": host,
                "port": port,
                "database": database,
                "username": username,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            },
        )

    async def connect(self) -> bool:
        
        Connect to PostgreSQL database.

        Returns:
            bool: True if connection successful
        
        if self.is_connected:
            return True

        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=os.getenv("POSTGRESQL_PASSWORD", "")
                min_size=self.min_connections,
                max_size=self.max_connections,
                command_timeout=self.command_timeout,
            )

            # Test connection
            async with self.pool.acquire() as connection:
                await connection.execute("SELECT 1")

            self.is_connected = True

            logger.info("Database manager connected",
            extra={
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to connect to database: {e}",
                extra={
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
                exc_info=True,
            )
            return False

    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL database."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.is_connected = False

            logger.info("Database manager disconnected",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
            )

    @asynccontextmanager
    try:
        async def get_connection(self) -> Optional[Dict[str, Any]]:
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
        
        Get database connection from pool.

        Yields:
            asyncpg.Connection: Database connection
        
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                raise

        async with self.pool.acquire() as connection:
            yield connection

    try:
        async def execute_query(self, query: str, *args) -> list[dict[str, Any]]:
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
        
        Execute SELECT query and return results.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            list: Query results
        
        try:
            async with self.get_connection() as connection:
                rows = await connection.fetch(query, *args)

                # Convert to list of dictionaries
                results = [dict(row) for row in rows]

                # Add constitutional compliance to each result
                for result in results:
                    result["constitutional_hash"] = CONSTITUTIONAL_HASH

                logger.debug(
                    f"Query executed successfully: {len(results)} rows",
                    extra={
                        "query": query[:100],  # Log first 100 chars
                        "rows_returned": len(results),
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )

                return results

        except Exception as e:
            logger.error(
                f"Query execution error: {e}",
                extra={
                    "query": query[:100],
                    except Exception as e:
                        logger.error(f"Operation failed: {e}")
                        raise
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
                exc_info=True,
            )
            raise

    async def execute_command(self, command: str, *args) -> str:
        
        Execute INSERT/UPDATE/DELETE command.

        Args:
            command: SQL command
            *args: Command parameters

        Returns:
            str: Command result
        
        try:
            async with self.get_connection() as connection:
                result = await connection.execute(command, *args)

                logger.debug(
                    f"Command executed successfully: {result}",
                    extra={
                        "command": command[:100],
                        "result": result,
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )

                return result

        except Exception as e:
            logger.error(
                f"Command execution error: {e}",
                extra={
                    "command": command[:100],
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
                exc_info=True,
            )
            raise

    try:
        async def execute_transaction(self, commands: list[tuple]) -> list[str]:
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
        
        Execute multiple commands in a transaction.

        Args:
            commands: List of (command, args) tuples

        Returns:
            list: Command results
        
        try:
            async with self.get_connection() as connection:
                async with connection.transaction():
                    results = []

                    for command, args in commands:
                        result = await connection.execute(command, *args)
                        results.append(result)

                    logger.info(
                        f"Transaction executed successfully: {len(commands)} commands",
                        extra={
                            "commands_count": len(commands),
                            "constitutional_hash": CONSTITUTIONAL_HASH,
                        },
                    )

                    return results

        except Exception as e:
            logger.error(
                f"Transaction execution error: {e}",
                extra={
                    "commands_count": len(commands),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
                exc_info=True,
            )
            raise

    try:
        async def check_health(self) -> dict[str, Any]:
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
        
        Check database health.

        Returns:
            dict: Health check results
        
        try:
            if not self.is_connected:
                return ensure_constitutional_compliance(
                    {"status": "disconnected", "error": "Database not connected"}
                )

            async with self.get_connection() as connection:
                # Test basic connectivity
                await connection.execute("SELECT 1")

                # Get database info
                db_info = await connection.fetchrow(
                    
                    SELECT
                        current_database() as database_name,
                        current_user as current_user,
                        version() as version
                
                )

                # Get connection pool info
                pool_info = {
                    "size": self.pool.get_size(),
                    "min_size": self.pool.get_min_size(),
                    "max_size": self.pool.get_max_size(),
                    "idle_size": self.pool.get_idle_size(),
                }

                health_data = {
                    "status": "healthy",
                    "database_info": dict(db_info),
                    "pool_info": pool_info,
                    "connection_config": {
                        "host": self.host,
                        "port": self.port,
                        "database": self.database,
                        "username": self.username,
                    },
                }

                return ensure_constitutional_compliance(health_data)

        except Exception as e:
            logger.error(
                f"Database health check error: {e}",
                extra={"constitutional_hash": CONSTITUTIONAL_HASH},
                exc_info=True,
            )

            return ensure_constitutional_compliance(
                {"status": "unhealthy", "error": str(e)}
            )

    try:
        async def get_status(self) -> dict[str, Any]:
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
        """Get database manager status."""
        return ensure_constitutional_compliance(
            {
                "is_connected": self.is_connected,
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "username": self.username,
                "min_connections": self.min_connections,
                "max_connections": self.max_connections,
                "pool_size": self.pool.get_size() if self.pool else 0,
                "pool_idle_size": self.pool.get_idle_size() if self.pool else 0,
            }
        )

    async def __aenter__(self) -> Any:
        """Async context manager entry."""
        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Any:
        """Async context manager exit."""
        await self.disconnect()
