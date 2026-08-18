import pandas as pd


# ============================================================
# LOAD DATASET
# ============================================================

def load_dataset(file):

    filename = file.name.lower()

    if filename.endswith(".csv"):
        return pd.read_csv(file)

    elif filename.endswith(".xlsx"):
        return pd.read_excel(
            file,
            engine="openpyxl"
        )

    elif filename.endswith(".xls"):
        return pd.read_excel(file)

    raise ValueError(
        "Unsupported file format. "
        "Only CSV, XLS and XLSX files are supported."
    )


# ============================================================
# DATASET STATISTICS
# ============================================================

def get_dataset_stats(df):

    return {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "blank_cells": int(df.isna().sum().sum()),
    }


# ============================================================
# GET COLUMNS
# ============================================================

def get_columns(df):

    return [
        str(column)
        for column in df.columns
    ]


# ============================================================
# CLEAN WHITESPACE
# ============================================================

def clean_whitespace(df):

    df = df.copy()

    for column in df.columns:

        if (
            pd.api.types.is_object_dtype(df[column])
            or
            pd.api.types.is_string_dtype(df[column])
        ):

            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
                .str.replace(
                    r"\s+",
                    " ",
                    regex=True
                )
            )

    return df


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(df):

    return df.drop_duplicates().copy()


# ============================================================
# REMOVE BLANK ROWS
# ============================================================

def remove_blank_rows(df):

    df = df.copy()

    # Treat whitespace-only strings as blank
    for column in df.columns:

        if (
            pd.api.types.is_object_dtype(df[column])
            or
            pd.api.types.is_string_dtype(df[column])
        ):

            df[column] = df[column].replace(
                r"^\s*$",
                pd.NA,
                regex=True
            )

    return df.dropna(
        how="all"
    ).copy()


# ============================================================
# REMOVE EMPTY COLUMNS
# ============================================================

def remove_empty_columns(df):

    df = df.copy()

    for column in df.columns:

        if (
            pd.api.types.is_object_dtype(df[column])
            or
            pd.api.types.is_string_dtype(df[column])
        ):

            df[column] = df[column].replace(
                r"^\s*$",
                pd.NA,
                regex=True
            )

    return df.dropna(
        axis=1,
        how="all"
    ).copy()


# ============================================================
# REMOVE SELECTED COLUMNS
# ============================================================

def remove_columns(df, columns):

    df = df.copy()

    if not columns:
        return df

    valid_columns = [
        column
        for column in columns
        if column in df.columns
    ]

    if valid_columns:

        df = df.drop(
            columns=valid_columns
        )

    return df


# ============================================================
# REMOVE SELECTED ROWS
# ============================================================

def remove_rows(df, row_indexes):

    df = df.copy()

    if not row_indexes:
        return df

    valid_indexes = []

    for index in row_indexes:

        try:
            index = int(index)

            if index in df.index:
                valid_indexes.append(index)

        except (ValueError, TypeError):
            continue

    if valid_indexes:

        df = df.drop(
            index=valid_indexes
        )

    return df


# ============================================================
# CONVERT USER VALUE TO COLUMN TYPE
# ============================================================

def convert_value_to_column_dtype(
    value,
    series
):

    """
    Convert a user-entered replacement value to the
    datatype of the target column.

    This prevents errors such as:

        Invalid value 'UNKNOWN' for dtype 'float64'
    """

    if value is None:
        return value

    value = str(value).strip()

    # --------------------------------------------------------
    # EMPTY INPUT
    # --------------------------------------------------------

    if value == "":
        return ""

    dtype = series.dtype

    # --------------------------------------------------------
    # INTEGER
    # --------------------------------------------------------

    if pd.api.types.is_integer_dtype(dtype):

        try:

            number = float(value)

            if number.is_integer():

                return int(number)

            # If the column is integer but user entered
            # a decimal, keep it as text instead of crashing.
            return value

        except (ValueError, TypeError):

            return value

    # --------------------------------------------------------
    # FLOAT
    # --------------------------------------------------------

    if pd.api.types.is_float_dtype(dtype):

        try:

            return float(value)

        except (ValueError, TypeError):

            # IMPORTANT:
            # Do not attempt to insert a string into float64.
            #
            # Instead convert the whole column to object/string
            # in handle_missing_values before assignment.
            return value

    # --------------------------------------------------------
    # BOOLEAN
    # --------------------------------------------------------

    if pd.api.types.is_bool_dtype(dtype):

        lowered = value.lower()

        if lowered in {
            "true",
            "yes",
            "1",
        }:

            return True

        if lowered in {
            "false",
            "no",
            "0",
        }:

            return False

        return value

    # --------------------------------------------------------
    # DATETIME
    # --------------------------------------------------------

    if pd.api.types.is_datetime64_any_dtype(dtype):

        try:

            return pd.to_datetime(
                value
            )

        except (
            ValueError,
            TypeError,
        ):

            return value

    # --------------------------------------------------------
    # STRING / OBJECT
    # --------------------------------------------------------

    return value


# ============================================================
# HANDLE MISSING VALUES
# ============================================================

def handle_missing_values(
    df,
    replacement="",
    column_replacements=None,
):

    """
    Replace missing values safely.

    column_replacements:
        {
            "Age": "0",
            "Name": "UNKNOWN",
            "Salary": "0"
        }

    The function automatically handles datatype issues.
    """

    df = df.copy()

    if column_replacements is None:
        column_replacements = {}

    # ========================================================
    # APPLY INDIVIDUAL COLUMN VALUES
    # ========================================================

    for column, user_value in column_replacements.items():

        if column not in df.columns:
            continue

        if user_value is None:
            continue

        user_value = str(user_value).strip()

        if user_value == "":
            continue

        original_dtype = df[column].dtype

        converted_value = convert_value_to_column_dtype(
            user_value,
            df[column]
        )

        # ----------------------------------------------------
        # FLOAT / INTEGER / NUMERIC
        # ----------------------------------------------------

        if (
            pd.api.types.is_numeric_dtype(
                original_dtype
            )
        ):

            try:

                if pd.api.types.is_integer_dtype(
                    original_dtype
                ):

                    converted_value = int(
                        float(converted_value)
                    )

                else:

                    converted_value = float(
                        converted_value
                    )

            except (
                ValueError,
                TypeError,
            ):

                # User entered text such as UNKNOWN.
                #
                # Convert the column to object before
                # inserting the value.
                df[column] = df[column].astype(
                    object
                )

                converted_value = user_value

        # ----------------------------------------------------
        # DATETIME
        # ----------------------------------------------------

        elif pd.api.types.is_datetime64_any_dtype(
            original_dtype
        ):

            try:

                converted_value = pd.to_datetime(
                    converted_value
                )

            except (
                ValueError,
                TypeError,
            ):

                df[column] = df[column].astype(
                    object
                )

                converted_value = user_value

        # ----------------------------------------------------
        # BOOLEAN
        # ----------------------------------------------------

        elif pd.api.types.is_bool_dtype(
            original_dtype
        ):

            if not isinstance(
                converted_value,
                bool
            ):

                df[column] = df[column].astype(
                    object
                )

                converted_value = user_value

        # ----------------------------------------------------
        # APPLY
        # ----------------------------------------------------

        df.loc[
            df[column].isna(),
            column
        ] = converted_value

    # ========================================================
    # APPLY "APPLY TO ALL"
    # ========================================================

    if replacement is not None:

        replacement = str(
            replacement
        ).strip()

    if replacement:

        for column in df.columns:

            missing_mask = df[column].isna()

            if not missing_mask.any():
                continue

            original_dtype = df[column].dtype

            # ------------------------------------------------
            # NUMERIC COLUMN
            # ------------------------------------------------

            if pd.api.types.is_numeric_dtype(
                original_dtype
            ):

                try:

                    if pd.api.types.is_integer_dtype(
                        original_dtype
                    ):

                        converted = int(
                            float(replacement)
                        )

                    else:

                        converted = float(
                            replacement
                        )

                except (
                    ValueError,
                    TypeError,
                ):

                    # Example:
                    # User enters UNKNOWN
                    # for a float column.
                    #
                    # Convert to object first.
                    df[column] = df[column].astype(
                        object
                    )

                    converted = replacement

            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            elif pd.api.types.is_datetime64_any_dtype(
                original_dtype
            ):

                try:

                    converted = pd.to_datetime(
                        replacement
                    )

                except (
                    ValueError,
                    TypeError,
                ):

                    df[column] = df[column].astype(
                        object
                    )

                    converted = replacement

            # ------------------------------------------------
            # BOOLEAN
            # ------------------------------------------------

            elif pd.api.types.is_bool_dtype(
                original_dtype
            ):

                lowered = replacement.lower()

                if lowered in {
                    "true",
                    "yes",
                    "1",
                }:

                    converted = True

                elif lowered in {
                    "false",
                    "no",
                    "0",
                }:

                    converted = False

                else:

                    df[column] = df[column].astype(
                        object
                    )

                    converted = replacement

            # ------------------------------------------------
            # TEXT / OBJECT
            # ------------------------------------------------

            else:

                converted = replacement

            # ------------------------------------------------
            # APPLY
            # ------------------------------------------------

            df.loc[
                missing_mask,
                column
            ] = converted

    return df


# ============================================================
# CLEAN DATAFRAME
# ============================================================




# ============================================================
# CONVERT REPLACEMENT TO COLUMN DATA TYPE
# ============================================================

def convert_replacement_value(
    value,
    series,
):
    """
    Convert a user-entered replacement value
    to a type compatible with the column.

    Examples:

        100       -> numeric column -> 100
        10.5      -> float column   -> 10.5
        true      -> boolean column -> True
        2026-01-01 -> datetime      -> Timestamp

    If conversion is not possible, the value
    is returned as a string.
    """

    if value is None:
        return value

    value = str(value).strip()

    if value == "":
        return ""

    dtype = series.dtype

    # --------------------------------------------------------
    # INTEGER
    # --------------------------------------------------------

    if pd.api.types.is_integer_dtype(dtype):

        try:
            return int(value)

        except (ValueError, TypeError):

            return value


    # --------------------------------------------------------
    # FLOAT
    # --------------------------------------------------------

    if pd.api.types.is_float_dtype(dtype):

        try:
            return float(value)

        except (ValueError, TypeError):

            return value


    # --------------------------------------------------------
    # BOOLEAN
    # --------------------------------------------------------

    if pd.api.types.is_bool_dtype(dtype):

        value_lower = value.lower()

        if value_lower in {
            "true",
            "yes",
            "1",
        }:

            return True

        if value_lower in {
            "false",
            "no",
            "0",
        }:

            return False

        return value


    # --------------------------------------------------------
    # DATETIME
    # --------------------------------------------------------

    if pd.api.types.is_datetime64_any_dtype(dtype):

        try:

            return pd.to_datetime(
                value
            )

        except (
            ValueError,
            TypeError,
        ):

            return value


    # --------------------------------------------------------
    # EVERYTHING ELSE
    # --------------------------------------------------------

    return value


# ============================================================
# HANDLE MISSING VALUES
# ============================================================

def handle_missing_values(
    df,
    replacement="",
    column_replacements=None,
):
    """
    Replace missing values.

    Supports:

    1. One value for all missing cells.
    2. Different values for different columns.

    Replacement values are converted to the
    appropriate column data type where possible.
    """

    df = df.copy()

    column_replacements = (
        column_replacements
        or {}
    )


    # --------------------------------------------------------
    # COLUMN-SPECIFIC VALUES
    # --------------------------------------------------------

    for column, value in column_replacements.items():

        if column not in df.columns:
            continue

        converted_value = (
            convert_replacement_value(
                value,
                df[column],
            )
        )

        try:

            df[column] = df[column].fillna(
                converted_value
            )

        except (
            TypeError,
            ValueError,
        ):

            # If the value cannot fit the original
            # dtype, convert the column to object/string.
            df[column] = (
                df[column]
                .astype("object")
                .where(
                    df[column].notna(),
                    converted_value,
                )
            )


    # --------------------------------------------------------
    # APPLY ONE VALUE TO ALL REMAINING MISSING CELLS
    # --------------------------------------------------------

    if replacement is not None:

        replacement = str(
            replacement
        ).strip()

        if replacement != "":

            for column in df.columns:

                # Don't overwrite columns that already
                # received a column-specific replacement.

                if column in column_replacements:
                    continue

                converted_value = (
                    convert_replacement_value(
                        replacement,
                        df[column],
                    )
                )

                try:

                    df[column] = (
                        df[column]
                        .fillna(
                            converted_value
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    df[column] = (
                        df[column]
                        .astype("object")
                        .where(
                            df[column].notna(),
                            converted_value,
                        )
                    )

    return df


# ============================================================
# CLEAN DATASET
# ============================================================

def clean_dataframe(
    df,
    remove_duplicate_rows=True,
    remove_blank=True,
    clean_spaces=True,
    handle_null_values=False,
    replacement="",
    columns_to_remove=None,
    remove_empty_columns_flag=False,
    normalize_column_names=False,
    column_replacements=None,
):
    """
    Run all selected cleaning operations.
    """

    cleaned_df = df.copy()


    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    if remove_duplicate_rows:

        cleaned_df = remove_duplicates(
            cleaned_df
        )


    # --------------------------------------------------------
    # REMOVE BLANK ROWS
    # --------------------------------------------------------

    if remove_blank:

        cleaned_df = remove_blank_rows(
            cleaned_df
        )


    # --------------------------------------------------------
    # REMOVE WHITESPACE
    # --------------------------------------------------------

    if clean_spaces:

        cleaned_df = clean_whitespace(
            cleaned_df
        )


    # --------------------------------------------------------
    # NORMALIZE COLUMN NAMES
    # --------------------------------------------------------

    if normalize_column_names:

        cleaned_df.columns = [

            str(column)
            .strip()
            .lower()
            .replace(" ", "_")

            for column in cleaned_df.columns

        ]


    # --------------------------------------------------------
    # REMOVE EMPTY COLUMNS
    # --------------------------------------------------------

    if remove_empty_columns_flag:

        cleaned_df = remove_empty_columns(
            cleaned_df
        )


    # --------------------------------------------------------
    # HANDLE MISSING VALUES
    # --------------------------------------------------------

    if (
        handle_null_values
        or
        replacement
        or
        column_replacements
    ):

        cleaned_df = handle_missing_values(

            cleaned_df,

            replacement=replacement,

            column_replacements=(
                column_replacements
                or {}
            ),

        )


    # --------------------------------------------------------
    # REMOVE SELECTED COLUMNS
    # --------------------------------------------------------

    if columns_to_remove:

        cleaned_df = remove_columns(
            cleaned_df,
            columns_to_remove
        )


    return cleaned_df


# ============================================================
# PREVIEW
# ============================================================

def generate_preview(
    df,
    rows=5
):

    preview_df = df.head(rows)

    return preview_df.to_html(
        classes=[
            "table",
            "table-striped",
            "table-hover",
            "align-middle",
            "mb-0",
        ],
        index=False,
        border=0,
    )


# ============================================================
# ANALYZE DATAFRAME
# ============================================================

def analyze_dataframe(df):

    if df is None:
        return {}

    total_rows = len(df)

    total_columns = len(
        df.columns
    )

    missing_cells = int(
        df.isna()
        .sum()
        .sum()
    )

    empty_string_cells = 0

    for column in df.columns:

        try:

            empty_string_cells += int(
                df[column]
                .astype(str)
                .str.strip()
                .eq("")
                .sum()
            )

        except Exception:
            pass

    blank_cells = (
        missing_cells
        + empty_string_cells
    )

    duplicate_rows = int(
        df.duplicated().sum()
    )

    empty_rows = int(
        df.isna()
        .all(axis=1)
        .sum()
    )

    empty_columns = int(
        df.isna()
        .all(axis=0)
        .sum()
    )

    columns = []

    for column in df.columns:

        series = df[column]

        columns.append({

            "name":
                str(column),

            "dtype":
                str(series.dtype),

            "missing":
                int(
                    series.isna().sum()
                ),

            "unique":
                int(
                    series.nunique(
                        dropna=True
                    )
                ),

            "duplicate":
                int(
                    series.duplicated().sum()
                ),

        })

    return {

        "total_rows":
            total_rows,

        "total_columns":
            total_columns,

        "missing_cells":
            missing_cells,

        "blank_cells":
            blank_cells,

        "duplicate_rows":
            duplicate_rows,

        "empty_rows":
            empty_rows,

        "empty_columns":
            empty_columns,

        "columns":
            columns,

    }