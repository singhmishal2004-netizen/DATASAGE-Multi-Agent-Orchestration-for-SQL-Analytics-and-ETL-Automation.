
import os
import requests
import pandas as pd

from Guardrails.etl_guard import (
    resolve_data_path,
    validate_format,
    validate_transformation_plan
)


class ETLTools:

    def __init__(self):
        pass

    # -------------------------------- EXTRACTION --------------------------------

    def extract_load(self, url: str, output_folder: str, format: str):
        """
        Extract data from an API and save it in the requested format.
        """

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )

        try:
            # Validate output format.
            if not validate_format(format):
                return f"Unsupported format: {format}"

            # Restrict output path to the data directory.
            output_path = resolve_data_path(
                project_root,
                output_folder
            )

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()

            os.makedirs(output_path, exist_ok=True)

            filename = os.path.join(
                output_path,
                f"extracted_data.{format}"
            )

            records = (
                data.get('results', data.get('data', data))
                if isinstance(data, dict)
                else data
            )

            df = pd.json_normalize(records)

            if format == "csv":
                df.to_csv(filename, index=False)

            elif format == "json":
                df.to_json(
                    filename,
                    orient="records",
                    lines=True
                )

            elif format == "parquet":
                df.to_parquet(filename, index=False)

            return (
                f"Data successfully extracted and saved to {filename}"
            )

        except requests.exceptions.RequestException as e:
            return f"Failed to extract data: {e}"

        except Exception as e:
            return f"ETL extraction failed: {e}"

    # -------------------------------- DATA CONTEXT --------------------------------

    def transform_load_context(self, file_path: str):
        """
        Read an existing file and return its first three rows
        for LLM transformation planning.
        """

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )

        try:
            # Restrict input file access to the data directory.
            input_path = resolve_data_path(
                project_root,
                file_path
            )

            file_extension = os.path.splitext(input_path)[1].lower()

            if file_extension == ".csv":
                df = pd.read_csv(input_path)

            elif file_extension == ".json":
                df = pd.read_json(input_path, lines=True)

            elif file_extension == ".parquet":
                df = pd.read_parquet(input_path)

            else:
                return f"Unsupported file format: {file_extension}"

            return str(df.head(3))

        except Exception as e:
            return f"Failed to read input file: {e}"

    # -------------------------------- TRANSFORMATION --------------------------------

    def execute_plan(
        self,
        input_file_path: str,
        output_folder: str,
        output_format: str,
        plan: dict
    ) -> str:

        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )

        try:
            # 1. Validate transformation plan.
            is_valid, reason = validate_transformation_plan(plan)

            if not is_valid:
                return f"Transformation blocked: {reason}"

            # 2. Validate output format.
            if not validate_format(output_format):
                return f"Unsupported output format: {output_format}"

            # 3. Restrict file access to the project data directory.
            input_path = resolve_data_path(
                project_root,
                input_file_path
            )

            output_path = resolve_data_path(
                project_root,
                output_folder
            )

            # 4. Read input data.
            extension = os.path.splitext(input_path)[1].lower()

            if extension == ".csv":
                df = pd.read_csv(input_path)

            elif extension == ".json":
                df = pd.read_json(input_path, lines=True)

            elif extension == ".parquet":
                df = pd.read_parquet(input_path)

            else:
                return f"Unsupported input format: {extension}"

            # 5. Execute only approved operations.
            for item in plan["operations"]:

                operation = item["operation"]

                if operation == "drop_duplicates":

                    df = df.drop_duplicates()

                elif operation == "drop_nulls":

                    columns = item["columns"]

                    if not set(columns).issubset(df.columns):
                        return "Transformation failed: Invalid column name."

                    df = df.dropna(subset=columns)

                elif operation == "fill_nulls":

                    column = item["column"]

                    if column not in df.columns:
                        return (
                            f"Transformation failed: "
                            f"Column '{column}' not found."
                        )

                    df[column] = df[column].fillna(item["value"])

                elif operation == "rename_columns":

                    mapping = item["mapping"]

                    if not set(mapping.keys()).issubset(df.columns):
                        return "Transformation failed: Invalid column name."

                    df = df.rename(columns=mapping)

                elif operation == "select_columns":

                    columns = item["columns"]

                    if not set(columns).issubset(df.columns):
                        return "Transformation failed: Invalid column name."

                    df = df[columns]

                elif operation == "sort_values":

                    columns = item["columns"]

                    if not set(columns).issubset(df.columns):
                        return "Transformation failed: Invalid column name."

                    df = df.sort_values(by=columns)

            # 6. Save transformed data.
            os.makedirs(output_path, exist_ok=True)

            filename = os.path.join(
                output_path,
                f"transformed_data.{output_format}"
            )

            if output_format == "csv":

                df.to_csv(filename, index=False)

            elif output_format == "json":

                df.to_json(
                    filename,
                    orient="records",
                    lines=True
                )

            elif output_format == "parquet":

                df.to_parquet(filename, index=False)

            return (
                f"Transformation successful. "
                f"Rows: {len(df)}. "
                f"Columns: {len(df.columns)}. "
                f"Saved to: {filename}"
            )

        except Exception as e:
            return f"Transformation failed: {str(e)}"


# -------------------------------- TESTING --------------------------------

if __name__ == "__main__":

    obj = ETLTools()

    path = "data/extract/extracted_data.csv"

    print(obj.transform_load_context(path))
