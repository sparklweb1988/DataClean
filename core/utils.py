from pathlib import Path
import uuid

import pandas as pd


# ============================================================
# READ CSV / EXCEL FILE
# ============================================================

def read_file(file_path, original_filename=None):
    """
    Read a CSV or Excel file into a pandas DataFrame.

    Supports:
        .csv
        .xlsx
        .xls
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    # --------------------------------------------------------
    # DETERMINE FILE TYPE
    # --------------------------------------------------------

    if original_filename:

        suffix = Path(
            original_filename
        ).suffix.lower()

    else:

        suffix = file_path.suffix.lower()

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    if suffix == ".csv":

        try:

            return pd.read_csv(
                file_path
            )

        except UnicodeDecodeError:

            # Try common alternative encoding
            return pd.read_csv(
                file_path,
                encoding="latin-1"
            )

    # --------------------------------------------------------
    # XLSX
    # --------------------------------------------------------

    elif suffix == ".xlsx":

        return pd.read_excel(
            file_path,
            engine="openpyxl"
        )

    # --------------------------------------------------------
    # XLS
    # --------------------------------------------------------

    elif suffix == ".xls":

        return pd.read_excel(
            file_path,
            engine="xlrd"
        )

    # --------------------------------------------------------
    # INVALID FILE
    # --------------------------------------------------------

    else:

        raise ValueError(
            "Unsupported file type. "
            "Only CSV, XLSX and XLS files are allowed."
        )


# ============================================================
# VALIDATE DATASET FILE
# ============================================================

def validate_dataset_file(uploaded_file):
    """
    Validate an uploaded CSV or Excel file.
    """

    if not uploaded_file:

        return (
            False,
            "No file was uploaded."
        )

    filename = uploaded_file.name

    suffix = Path(
        filename
    ).suffix.lower()

    allowed_extensions = {
        ".csv",
        ".xlsx",
        ".xls",
    }

    if suffix not in allowed_extensions:

        return (
            False,
            "Only CSV and Excel files are allowed."
        )

    return True, None


# ============================================================
# GENERATE CLEAN FILE NAME
# ============================================================

def generate_clean_filename(
    original_filename
):
    """
    Generate a unique filename for cleaned data.
    """

    original_path = Path(
        original_filename
    )

    stem = original_path.stem

    return (
        f"{stem}_cleaned_"
        f"{uuid.uuid4().hex[:8]}"
        f".xlsx"
    )