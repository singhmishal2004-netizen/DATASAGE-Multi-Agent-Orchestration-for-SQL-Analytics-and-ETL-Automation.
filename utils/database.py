
import os

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()


class DatabaseUtil:

    def __init__(self, db_config=None):
        self.db_config = db_config
        self.connection = None

        try:
            database_url = os.getenv("DATABASE_URL")

            if database_url:
                # Connect using Neon PostgreSQL connection string
                self.connection = psycopg2.connect(database_url)

            elif db_config:
                # Connect using local PostgreSQL configuration
                self.connection = psycopg2.connect(**db_config)

            else:
                raise ValueError(
                    "DATABASE_URL or db_config must be provided."
                )

            print("Database connected successfully!")

        except Exception as e:
            print(f"Error connecting to the database: {e}")
            self.connection = None

    def schema_details(self, schema_name):

        if self.connection is None:
            return "Database connection not available."

        schema_info_context = f"Database Schema: {schema_name}\n"
        cursor = None

        try:
            cursor = self.connection.cursor()

            # Fetch tables
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE';
                """,
                (schema_name,)
            )

            tables_list = cursor.fetchall()

            for table in tables_list:

                table_name = table[0]
                schema_info_context += f"\nTable: {table_name}\n"

                # Fetch columns and data types
                cursor.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s
                    AND table_name = %s;
                    """,
                    (schema_name, table_name)
                )

                columns_list = cursor.fetchall()

                for column in columns_list:
                    column_name, data_type = column

                    schema_info_context += (
                        f"  Column: {column_name}, "
                        f"Data Type: {data_type}\n"
                    )

                # Fetch sample data
                sample_query = sql.SQL(
                    "SELECT * FROM {}.{} LIMIT 5;"
                ).format(
                    sql.Identifier(schema_name),
                    sql.Identifier(table_name)
                )

                cursor.execute(sample_query)
                sample_data = cursor.fetchall()

                schema_info_context += "  Sample Data:\n"

                for row in sample_data:
                    schema_info_context += f"    {row}\n"

        except Exception as e:
            print(f"Error fetching schema details: {e}")
            schema_info_context = (
                f"Error fetching schema details: {e}"
            )

        finally:
            if cursor:
                cursor.close()

        return schema_info_context

    def execute_sql(self, query):

        if self.connection is None:
            return None

        cursor = None

        try:
            cursor = self.connection.cursor()
            cursor.execute(query)

            if cursor.description:
                result = cursor.fetchall()
                return str(result)

            self.connection.commit()
            return "Query executed successfully."

        except Exception as e:
            self.connection.rollback()
            print(f"Error executing query: {e}")
            return f"SQL Execution Error: {str(e)}"

        finally:
            if cursor:
                cursor.close()

    def close_connection(self):

        if self.connection:
            self.connection.close()
            print("Database connection closed.")


# -------------------------------
# Testing the DatabaseUtil class
# -------------------------------

if __name__ == "__main__":

    # Uses DATABASE_URL from your .env file
    obj = DatabaseUtil()

    if obj.connection:

        try:
            # Test 1: Fetch database schema
            result = obj.schema_details("public")

            with open("test_schema_details.txt", "w") as f:
                f.write(result)

            print("\nSchema details saved to test_schema_details.txt")

            # Test 2: Execute SQL query
            query_result = obj.execute_sql(
                """
                SELECT *
                FROM information_schema.tables
                WHERE table_schema = 'public'
                LIMIT 5;
                """
            )

            print("\nQuery Result:")
            print(query_result)

        finally:
            obj.close_connection()
