from pathlib import Path
from datetime import timedelta
import os
import traceback
import uuid
import io
import pickle

import pandas as pd
import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from .models import (
    Subscription,
    SubscriptionPlan,
    Payment,
    BlogPost,
)

from .cleaning import (
    load_dataset,
    get_dataset_stats,
    get_columns,
    generate_preview,
    clean_dataframe,
    analyze_dataframe,
)

import tempfile
from .utils import read_file
# ============================================================
# CACHE CONFIGURATION
# ============================================================

# How long uploaded/cleaned datasets remain in cache.
# 30 minutes is usually enough for a normal cleaning session.
DATASET_CACHE_TIMEOUT = 60 * 30


# ============================================================
# CACHE HELPERS
# ============================================================

def dataset_cache_key(dataset_id):
    """
    Generate a unique cache key for a dataset.
    """

    return f"dataclean_dataset_{dataset_id}"


def cleaned_cache_key(dataset_id):
    """
    Generate a unique cache key for a cleaned dataset.
    """

    return f"dataclean_cleaned_{dataset_id}"


def store_dataset(dataset_id, dataframe):
    """
    Store a DataFrame temporarily in Django cache.

    The DataFrame is serialized with pickle so that it can
    be stored even when using cache backends that do not
    directly support DataFrame objects.
    """

    cache.set(
        dataset_cache_key(dataset_id),
        pickle.dumps(dataframe),
        timeout=DATASET_CACHE_TIMEOUT,
    )


def get_stored_dataset(dataset_id):
    """
    Retrieve an uploaded DataFrame from cache.
    """

    data = cache.get(
        dataset_cache_key(dataset_id)
    )

    if data is None:
        return None

    try:
        return pickle.loads(data)

    except Exception:
        return None


def delete_stored_dataset(dataset_id):
    """
    Remove uploaded dataset from cache.
    """

    cache.delete(
        dataset_cache_key(dataset_id)
    )


def store_cleaned_dataset(dataset_id, dataframe):
    """
    Store cleaned DataFrame temporarily in cache.
    """

    cache.set(
        cleaned_cache_key(dataset_id),
        pickle.dumps(dataframe),
        timeout=DATASET_CACHE_TIMEOUT,
    )


def get_cleaned_dataset(dataset_id):
    """
    Retrieve cleaned DataFrame from cache.
    """

    data = cache.get(
        cleaned_cache_key(dataset_id)
    )

    if data is None:
        return None

    try:
        return pickle.loads(data)

    except Exception:
        return None


def delete_cleaned_dataset(dataset_id):
    """
    Remove cleaned dataset from cache.
    """

    cache.delete(
        cleaned_cache_key(dataset_id)
    )


# ============================================================
# READ UPLOADED FILE DIRECTLY FROM MEMORY
# ============================================================

def read_uploaded_file(uploaded_file):
    """
    Read CSV or Excel directly from the uploaded file.

    Nothing is written to MEDIA_ROOT or the project directory.
    """

    filename = uploaded_file.name

    suffix = Path(filename).suffix.lower()

    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    if suffix == ".csv":

        file_data = uploaded_file.read()

        if not file_data:
            raise ValueError(
                "The uploaded file is empty."
            )

        file_object = io.BytesIO(
            file_data
        )

        try:

            df = pd.read_csv(
                file_object
            )

        except UnicodeDecodeError:

            file_object.seek(0)

            df = pd.read_csv(
                file_object,
                encoding="latin-1",
            )

        return df

    # --------------------------------------------------------
    # READ XLSX
    # --------------------------------------------------------

    if suffix == ".xlsx":

        file_data = uploaded_file.read()

        if not file_data:
            raise ValueError(
                "The uploaded file is empty."
            )

        file_object = io.BytesIO(
            file_data
        )

        return pd.read_excel(
            file_object,
            engine="openpyxl",
        )

    # --------------------------------------------------------
    # READ XLS
    # --------------------------------------------------------

    if suffix == ".xls":

        file_data = uploaded_file.read()

        if not file_data:
            raise ValueError(
                "The uploaded file is empty."
            )

        file_object = io.BytesIO(
            file_data
        )

        return pd.read_excel(
            file_object,
            engine="xlrd",
        )

    raise ValueError(
        "Only CSV, XLSX and XLS files are supported."
    )


# ============================================================
# PLAN CONFIGURATION
# ============================================================

PLANS = {

    "free": {
        "name": "Free",
        "price": 0,
        "max_rows": 1000,
        "max_columns": 10,
        "duration_days": 30,
    },

    "basic": {
        "name": "Basic",
        "price": 5000,
        "max_rows": 10000,
        "max_columns": 30,
        "duration_days": 30,
    },

    "pro": {
        "name": "Pro",
        "price": 15000,
        "max_rows": 100000,
        "max_columns": 100,
        "duration_days": 30,
    },

    "business": {
        "name": "Business",
        "price": 25000,
        "max_rows": 1000000,
        "max_columns": 500,
        "duration_days": 30,
    },
}


# ============================================================
# PAYSTACK SETTINGS
# ============================================================

PAYSTACK_SECRET_KEY = getattr(
    settings,
    "PAYSTACK_SECRET_KEY",
    os.getenv("PAYSTACK_SECRET_KEY", ""),
)

BASE_URL = getattr(
    settings,
    "BASE_URL",
    os.getenv(
        "BASE_URL",
        "http://127.0.0.1:8000",
    ),
)

PAYSTACK_BASE_URL = "https://api.paystack.co"


# ============================================================
# HOME
# ============================================================

def home(request):

    return render(
        request,
        "home.html",
        {
            "plans": PLANS,
        },
    )


# ============================================================
# ABOUT
# ============================================================

def about(request):

    return render(
        request,
        "about.html",
    )


# ============================================================
# CONTACT
# ============================================================

def contact(request):

    if request.method == "POST":

        name = request.POST.get(
            "name",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip()

        subject = request.POST.get(
            "subject",
            "",
        ).strip()

        message = request.POST.get(
            "message",
            "",
        ).strip()

        if not name or not email or not message:

            messages.error(
                request,
                "Please fill in all required fields.",
            )

            return redirect("contact")

        try:

            send_mail(
                subject or "DataClean Pro Contact",

                (
                    f"Name: {name}\n"
                    f"Email: {email}\n\n"
                    f"{message}"
                ),

                settings.DEFAULT_FROM_EMAIL,

                [
                    settings.DEFAULT_FROM_EMAIL,
                ],

                fail_silently=False,
            )

            messages.success(
                request,
                "Your message has been sent successfully.",
            )

            return redirect("contact")

        except Exception:

            traceback.print_exc()

            messages.error(
                request,
                "Unable to send your message. Please try again.",
            )

    return render(
        request,
        "contact.html",
    )


# ============================================================
# PRIVACY
# ============================================================

def privacy(request):

    return render(
        request,
        "privacy.html",
    )


# ============================================================
# REGISTER
# ============================================================

def register(request):

    if request.user.is_authenticated:

        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        email = request.POST.get(
            "email",
            "",
        ).strip().lower()

        password = request.POST.get(
            "password",
            "",
        )

        confirm_password = request.POST.get(
            "confirm_password",
            "",
        )

        if (
            not username
            or not email
            or not password
            or not confirm_password
        ):

            messages.error(
                request,
                "All fields are required.",
            )

            return render(
                request,
                "register.html",
            )

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match.",
            )

            return render(
                request,
                "register.html",
            )

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Username already exists.",
            )

            return render(
                request,
                "register.html",
            )

        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists.",
            )

            return render(
                request,
                "register.html",
            )

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        messages.success(
            request,
            "Account created successfully. Please login to continue.",
        )

        return redirect("login")

    return render(
        request,
        "register.html",
    )


# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    if request.user.is_authenticated:

        return redirect("dashboard")

    if request.method == "POST":

        email = request.POST.get(
            "email",
            "",
        ).strip().lower()

        password = request.POST.get(
            "password",
            "",
        )

        if not email or not password:

            messages.error(
                request,
                "Email and password are required.",
            )

            return render(
                request,
                "login.html",
            )

        try:

            user = User.objects.get(
                email__iexact=email
            )

        except User.DoesNotExist:

            messages.error(
                request,
                "Invalid email or password.",
            )

            return render(
                request,
                "login.html",
            )

        authenticated_user = authenticate(
            request,
            username=user.username,
            password=password,
        )

        if authenticated_user is None:

            messages.error(
                request,
                "Invalid email or password.",
            )

            return render(
                request,
                "login.html",
            )

        login(
            request,
            authenticated_user,
        )

        subscription = (
            Subscription.objects
            .filter(
                user=authenticated_user,
                status="active",
                expires_at__gt=timezone.now(),
            )
            .order_by("-expires_at")
            .first()
        )

        if subscription is None:

            messages.info(
                request,
                "Please choose a DataClean Pro plan to continue.",
            )

            return redirect("pricing")

        return redirect("dashboard")

    return render(
        request,
        "login.html",
    )


# ============================================================
# LOGOUT
# ============================================================

@login_required
def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully.",
    )

    return redirect("home")


# ============================================================
# GET USER PLAN
# ============================================================

def get_user_plan(user):

    subscription = (
        Subscription.objects
        .filter(
            user=user,
            status="active",
            expires_at__gt=timezone.now(),
        )
        .select_related("plan")
        .order_by("-expires_at")
        .first()
    )

    if not subscription:

        return {
            "plan": "free",
            "name": "Free",
            "status": "inactive",
            "max_rows": 0,
            "max_columns": 0,
            "subscription": None,
        }

    plan_name = subscription.plan.name.lower()

    plan_config = PLANS.get(
        plan_name,
        PLANS["free"],
    )

    return {
        "plan": plan_name,
        "name": plan_config["name"],
        "status": "active",
        "max_rows": plan_config["max_rows"],
        "max_columns": plan_config["max_columns"],
        "subscription": subscription,
    }


# ============================================================
# PRICING
# ============================================================

def pricing(request):

    subscription = None

    if request.user.is_authenticated:

        subscription = (
            Subscription.objects
            .filter(
                user=request.user,
                status="active",
                expires_at__gt=timezone.now(),
            )
            .select_related("plan")
            .order_by("-expires_at")
            .first()
        )

    return render(
        request,
        "pricing.html",
        {
            "plans": PLANS,
            "subscription": subscription,
        },
    )


# ============================================================
# ACTIVATE FREE PLAN
# ============================================================

@login_required
def activate_free_plan(request):

    if request.method != "POST":

        return redirect("pricing")

    active_subscription = (
        Subscription.objects
        .filter(
            user=request.user,
            status="active",
            expires_at__gt=timezone.now(),
        )
        .first()
    )

    if active_subscription:

        messages.info(
            request,
            "You already have an active subscription.",
        )

        return redirect("dashboard")

    free_plan = (
        SubscriptionPlan.objects
        .filter(
            name__iexact="free"
        )
        .first()
    )

    if not free_plan:

        messages.error(
            request,
            "Free plan is not available.",
        )

        return redirect("pricing")

    expires_at = (
        timezone.now()
        + timedelta(
            days=PLANS["free"]["duration_days"]
        )
    )

    reference = (
        "FREE-"
        + uuid.uuid4().hex
    )

    Subscription.objects.update_or_create(

        user=request.user,

        defaults={
            "plan": free_plan,
            "status": "active",
            "expires_at": expires_at,
            "payment_reference": reference,
        },
    )

    messages.success(
        request,
        "Your Free Plan has been activated successfully.",
    )

    return redirect("dashboard")


# ============================================================
# INITIALIZE PAYSTACK PAYMENT
# ============================================================

@login_required
def initialize_payment(request):

    if request.method != "POST":

        return redirect("pricing")

    plan_name = request.POST.get(
        "plan",
        "",
    ).strip().lower()

    if not plan_name:

        messages.error(
            request,
            "Please select a subscription plan.",
        )

        return redirect("pricing")

    plan = get_object_or_404(
        SubscriptionPlan,
        name=plan_name,
        is_active=True,
    )

    if plan.name == "free":

        messages.info(
            request,
            "The free plan does not require payment.",
        )

        return redirect("activate_free_plan")

    if plan.price <= 0:

        messages.error(
            request,
            "This subscription plan does not have a valid price.",
        )

        return redirect("pricing")

    reference = (
        f"DCP-{request.user.id}-"
        f"{uuid.uuid4().hex[:12].upper()}"
    )

    payment = Payment.objects.create(

        user=request.user,

        reference=reference,

        amount=plan.price,

        currency="NGN",

        plan_name=plan.name,

        status="pending",
    )

    if not settings.PAYSTACK_SECRET_KEY:

        payment.status = "failed"

        payment.save(
            update_fields=[
                "status"
            ]
        )

        messages.error(
            request,
            "Payment system is not configured.",
        )

        return redirect("pricing")

    url = (
        "https://api.paystack.co/"
        "transaction/initialize"
    )

    headers = {

        "Authorization":
            f"Bearer {settings.PAYSTACK_SECRET_KEY}",

        "Content-Type":
            "application/json",
    }

    data = {

        "email":
            request.user.email,

        "amount":
            int(plan.price * 100),

        "reference":
            reference,

        "callback_url":
            f"{settings.BASE_URL}/payments/callback/",
    }

    try:

        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=30,
        )

        result = response.json()

    except requests.RequestException:

        payment.status = "failed"

        payment.save(
            update_fields=[
                "status"
            ]
        )

        messages.error(
            request,
            "Unable to connect to the payment provider.",
        )

        return redirect("pricing")

    if result.get("status") is True:

        authorization_url = (
            result["data"]["authorization_url"]
        )

        return redirect(
            authorization_url
        )

    payment.status = "failed"

    payment.save(
        update_fields=[
            "status"
        ]
    )

    messages.error(
        request,
        result.get(
            "message",
            "Payment initialization failed.",
        ),
    )

    return redirect("pricing")


# ============================================================
# DASHBOARD
# ============================================================

@login_required
def dashboard(request):

    plan = get_user_plan(
        request.user
    )

    subscription = plan.get(
        "subscription"
    )

    payments = (
        Payment.objects
        .filter(
            user=request.user,
            status="success",
        )
        .order_by("-created_at")
    )

    try:

        datasets = (
            request.user.datasets
            .order_by("-uploaded_at")
        )

    except AttributeError:

        datasets = []

    rows_used = 0

    for dataset in datasets:

        try:

            rows_used += int(
                dataset.total_rows or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            pass

    rows_limit = plan.get(
        "max_rows",
        0,
    )

    if rows_limit:

        rows_remaining = max(
            rows_limit - rows_used,
            0,
        )

    else:

        rows_remaining = 0

    if rows_limit:

        rows_percentage = min(
            int(
                (rows_used / rows_limit)
                * 100
            ),
            100,
        )

    else:

        rows_percentage = 0

    try:

        files_cleaned = (
            request.user.datasets
            .filter(
                status="cleaned"
            )
            .count()
        )

    except AttributeError:

        files_cleaned = 0

    max_file_size = "100 MB"

    return render(
        request,
        "dashboard.html",
        {

            "plan":
                plan,

            "subscription":
                subscription,

            "payments":
                payments,

            "datasets":
                datasets,

            "rows_used":
                rows_used,

            "rows_limit":
                rows_limit,

            "rows_remaining":
                rows_remaining,

            "rows_percentage":
                rows_percentage,

            "files_cleaned":
                files_cleaned,

            "max_file_size":
                max_file_size,
        },
    )


# ============================================================
# DATAFRAME PREVIEW
# ============================================================

def dataframe_preview(df, limit=5):

    preview_df = (
        df.head(limit)
        .copy()
    )

    rows = []

    for _, row in preview_df.iterrows():

        row_data = {}

        for column in preview_df.columns:

            value = row[column]

            if pd.isna(value):

                value = ""

            else:

                value = str(value)

            row_data[str(column)] = value

        rows.append(
            row_data
        )

    columns = []

    for index, column in enumerate(
        df.columns
    ):

        columns.append({

            "index":
                index,

            "name":
                str(column),
        })

    return columns, rows


# ============================================================
# UPLOAD PAGE
# ============================================================

@login_required
def upload_page(request):

    plan = get_user_plan(
        request.user
    )

    return render(
        request,
        "upload.html",
        {
            "plan":
                plan,
        },
    )


# ============================================================
# PROCESS UPLOAD
# ============================================================

@login_required
def upload_dataset(request):

    if request.method != "POST":

        return redirect(
            "upload"
        )

    # ========================================================
    # PLAN
    # ========================================================

    plan = get_user_plan(
        request.user
    )

    # ========================================================
    # CHECK ACTIVE PLAN
    # ========================================================

    if plan["status"] != "active":

        messages.error(
            request,
            "Please choose an active plan before uploading a dataset.",
        )

        return redirect(
            "pricing"
        )

    # ========================================================
    # FILE
    # ========================================================

    uploaded_file = request.FILES.get(
        "file"
    )

    if not uploaded_file:

        messages.error(
            request,
            "Please select a file.",
        )

        return redirect(
            "upload"
        )

    # ========================================================
    # FILE EXTENSION
    # ========================================================

    filename = uploaded_file.name

    suffix = Path(
        filename
    ).suffix.lower()

    allowed_extensions = (
        ".csv",
        ".xlsx",
        ".xls",
    )

    if suffix not in allowed_extensions:

        messages.error(
            request,
            "Only CSV and Excel files are allowed.",
        )

        return redirect(
            "upload"
        )

    # ========================================================
    # DATASET ID
    # ========================================================

    dataset_id = uuid.uuid4().hex

    try:

        # ====================================================
        # READ FILE DIRECTLY INTO MEMORY
        # ====================================================

        df = read_uploaded_file(
            uploaded_file
        )

        if df is None:

            raise ValueError(
                "Unable to read uploaded file."
            )

        # ====================================================
        # CHECK ROW LIMIT
        # ====================================================

        max_rows = plan["max_rows"]

        if (
            max_rows
            and len(df) > max_rows
        ):

            messages.error(
                request,
                (
                    f"Your {plan['name']} plan allows "
                    f"a maximum of {max_rows:,} rows per dataset."
                ),
            )

            return redirect(
                "upload"
            )

        # ====================================================
        # CHECK COLUMN LIMIT
        # ====================================================

        max_columns = plan["max_columns"]

        if (
            max_columns
            and len(df.columns) > max_columns
        ):

            messages.error(
                request,
                (
                    f"Your {plan['name']} plan allows "
                    f"a maximum of {max_columns:,} columns per dataset."
                ),
            )

            return redirect(
                "upload"
            )

        # ====================================================
        # ANALYZE DATASET
        # ====================================================

        analysis = analyze_dataframe(
            df
        )

        # ====================================================
        # BUILD COLUMN INFORMATION
        # ====================================================

        columns = []

        for index, column in enumerate(
            df.columns
        ):

            series = df[column]

            columns.append({

                "index":
                    index,

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

        # ====================================================
        # BUILD 5-ROW PREVIEW
        # ====================================================

        preview_df = (
            df.head(5)
            .copy()
        )

        rows = []

        for _, row in preview_df.iterrows():

            row_data = []

            for column in df.columns:

                value = row[column]

                if pd.isna(value):

                    value = ""

                else:

                    value = str(value)

                row_data.append(
                    value
                )

            rows.append(
                row_data
            )

        # ====================================================
        # STORE DATAFRAME TEMPORARILY IN CACHE
        # ====================================================

        store_dataset(
            dataset_id,
            df,
        )

        # ====================================================
        # STORE SESSION DATA
        # ====================================================

        request.session[
            "dataset_id"
        ] = dataset_id

        request.session[
            "dataset_filename"
        ] = filename

        # ====================================================
        # RENDER PREVIEW
        # ====================================================

        return render(

            request,

            "preview.html",

            {

                "filename":
                    filename,

                "dataset_id":
                    dataset_id,

                "analysis":
                    analysis,

                "columns":
                    columns,

                "rows":
                    rows,

                "plan":
                    plan,
            },
        )

    except Exception as e:

        traceback.print_exc()

        # Remove temporary cached data
        delete_stored_dataset(
            dataset_id
        )

        messages.error(
            request,
            (
                "Unable to analyze the uploaded file. "
                f"{str(e)}"
            ),
        )

        return redirect(
            "upload"
        )


# ============================================================
# CONVERT VALUE TO DATA TYPE
# ============================================================

def convert_value_to_dtype(
    value,
    dtype,
):
    """
    Convert a user-entered missing value
    into the appropriate pandas data type.
    """

    if value is None:

        return None

    value = str(
        value
    ).strip()

    # ========================================================
    # INTEGER
    # ========================================================

    if pd.api.types.is_integer_dtype(
        dtype
    ):

        try:

            return int(
                float(value)
            )

        except (
            ValueError,
            TypeError,
        ):

            return value

    # ========================================================
    # FLOAT
    # ========================================================

    if pd.api.types.is_float_dtype(
        dtype
    ):

        try:

            return float(
                value
            )

        except (
            ValueError,
            TypeError,
        ):

            return value

    # ========================================================
    # BOOLEAN
    # ========================================================

    if pd.api.types.is_bool_dtype(
        dtype
    ):

        lower_value = value.lower()

        if lower_value in (
            "true",
            "yes",
            "1",
        ):

            return True

        if lower_value in (
            "false",
            "no",
            "0",
        ):

            return False

        return value

    # ========================================================
    # DATETIME
    # ========================================================

    if pd.api.types.is_datetime64_any_dtype(
        dtype
    ):

        try:

            return pd.to_datetime(
                value
            )

        except (
            ValueError,
            TypeError,
        ):

            return value

    # ========================================================
    # STRING / OBJECT
    # ========================================================

    return value


# ============================================================
# CLEAN DATASET
# ============================================================

@login_required
def clean_dataset(request):

    if request.method != "POST":

        return redirect(
            "upload"
        )

    # ========================================================
    # DATASET ID
    # ========================================================

    dataset_id = request.POST.get(
        "dataset_id"
    )

    if not dataset_id:

        messages.error(
            request,
            "Dataset ID is missing.",
        )

        return redirect(
            "upload"
        )

    # ========================================================
    # SECURITY CHECK
    # ========================================================

    session_dataset_id = (
        request.session.get(
            "dataset_id"
        )
    )

    if dataset_id != session_dataset_id:

        messages.error(
            request,
            "Invalid dataset.",
        )

        return redirect(
            "upload"
        )

    # ========================================================
    # GET DATASET FROM CACHE
    # ========================================================

    df = get_stored_dataset(
        dataset_id
    )

    if df is None:

        messages.error(
            request,
            (
                "Your dataset is no longer available. "
                "Please upload it again."
            ),
        )

        return redirect(
            "upload"
        )

    try:

        # ====================================================
        # CLEANING OPTIONS
        # ====================================================

        remove_duplicate_rows = (
            request.POST.get(
                "remove_duplicate_rows"
            )
            == "on"
        )

        remove_empty_rows = (
            request.POST.get(
                "remove_empty_rows"
            )
            == "on"
        )

        trim_whitespace = (
            request.POST.get(
                "trim_whitespace"
            )
            == "on"
        )

        remove_empty_columns = (
            request.POST.get(
                "remove_empty_columns"
            )
            == "on"
        )

        normalize_column_names = (
            request.POST.get(
                "normalize_column_names"
            )
            == "on"
        )

        # ====================================================
        # COLUMN-SPECIFIC REPLACEMENTS
        # ====================================================

        column_replacements = {}

        for key, value in request.POST.items():

            if not key.startswith(
                "replacement_"
            ):

                continue

            if value is None:

                continue

            value = str(
                value
            ).strip()

            if value == "":

                continue

            column_index = key.replace(
                "replacement_",
                "",
                1,
            )

            try:

                column_index = int(
                    column_index
                )

            except (
                ValueError,
                TypeError,
            ):

                continue

            if (
                column_index < 0
                or
                column_index >= len(df.columns)
            ):

                continue

            actual_column = (
                df.columns[
                    column_index
                ]
            )

            column_replacements[
                actual_column
            ] = value

        # ====================================================
        # CHECK WHETHER MISSING VALUES
        # SHOULD BE PROCESSED
        # ====================================================

        handle_null_values = bool(
            column_replacements
        )

        replacement = ""

        # ====================================================
        # CLEAN DATAFRAME
        # ====================================================

        cleaned_df = clean_dataframe(

            df,

            remove_duplicate_rows=(
                remove_duplicate_rows
            ),

            remove_blank=(
                remove_empty_rows
            ),

            clean_spaces=(
                trim_whitespace
            ),

            handle_null_values=(
                handle_null_values
            ),

            replacement=(
                replacement
            ),

            columns_to_remove=[],

            remove_empty_columns_flag=(
                remove_empty_columns
            ),

            normalize_column_names=(
                normalize_column_names
            ),

            column_replacements=(
                column_replacements
            ),
        )

        # ====================================================
        # STORE CLEANED DATAFRAME IN CACHE
        # ====================================================

        store_cleaned_dataset(
            dataset_id,
            cleaned_df,
        )

        # ====================================================
        # CLEANED PREVIEW
        # ====================================================

        preview_df = (
            cleaned_df
            .head(5)
            .copy()
        )

        rows = []

        for _, row in preview_df.iterrows():

            row_data = []

            for column in cleaned_df.columns:

                value = row[column]

                if pd.isna(value):

                    value = ""

                else:

                    value = str(value)

                row_data.append(
                    value
                )

            rows.append(
                row_data
            )

        # ====================================================
        # CLEANED COLUMNS
        # ====================================================

        columns = []

        for index, column in enumerate(
            cleaned_df.columns
        ):

            columns.append({

                "index":
                    index,

                "name":
                    str(column),
            })

        # ====================================================
        # STORE SESSION DATA
        # ====================================================

        cleaned_filename = (
            f"{Path(request.session.get('dataset_filename', 'dataset')).stem}_cleaned.xlsx"
        )

        request.session[
            "cleaned_filename"
        ] = cleaned_filename

        # ====================================================
        # FINAL REPORT
        # ====================================================

        report = {

            "original_rows":
                len(df),

            "cleaned_rows":
                len(cleaned_df),

            "rows_removed":
                len(df)
                -
                len(cleaned_df),

            "original_columns":
                len(df.columns),

            "cleaned_columns":
                len(cleaned_df.columns),

            "columns_removed":
                len(df.columns)
                -
                len(cleaned_df.columns),

            "duplicate_rows_removed":
                int(
                    df.duplicated().sum()
                )
                if remove_duplicate_rows
                else 0,

            "missing_values_remaining":
                int(
                    cleaned_df.isna()
                    .sum()
                    .sum()
                ),
        }

        # ====================================================
        # FINAL PAGE
        # ====================================================

        return render(

            request,

            "cleaned.html",

            {

                "output_filename":
                    cleaned_filename,

                "dataset_id":
                    dataset_id,

                "report":
                    report,

                "columns":
                    columns,

                "rows":
                    rows,

                "plan":
                    get_user_plan(
                        request.user
                    ),
            },
        )

    except Exception as e:

        traceback.print_exc()

        # Remove cleaned data if cleaning failed
        delete_cleaned_dataset(
            dataset_id
        )

        messages.error(

            request,

            (
                "Unable to clean dataset: "
                f"{str(e)}"
            ),
        )

        return redirect(
            "upload"
        )


# ============================================================
# DOWNLOAD CLEANED FILE
# ============================================================

@login_required
def download_file(
    request,
    filename,
):

    # --------------------------------------------------------
    # PREVENT PATH TRAVERSAL
    # --------------------------------------------------------

    safe_filename = Path(
        filename
    ).name

    # --------------------------------------------------------
    # GET DATASET ID FROM SESSION
    # --------------------------------------------------------

    dataset_id = request.session.get(
        "dataset_id"
    )

    if not dataset_id:

        raise Http404(
            "Dataset session has expired."
        )

    # --------------------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------------------

    expected_filename = (
        request.session.get(
            "cleaned_filename"
        )
    )

    if expected_filename != safe_filename:

        raise Http404(
            "You cannot access this file."
        )

    # --------------------------------------------------------
    # GET CLEANED DATASET FROM CACHE
    # --------------------------------------------------------

    cleaned_df = get_cleaned_dataset(
        dataset_id
    )

    if cleaned_df is None:

        raise Http404(
            "Cleaned dataset has expired. Please upload and clean the file again."
        )

    try:

        # ----------------------------------------------------
        # CREATE EXCEL FILE IN MEMORY
        # ----------------------------------------------------

        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl",
        ) as writer:

            cleaned_df.to_excel(
                writer,
                index=False,
                sheet_name="Cleaned Data",
            )

        # ----------------------------------------------------
        # MOVE BUFFER TO START
        # ----------------------------------------------------

        output.seek(0)

        # ----------------------------------------------------
        # RETURN FILE DIRECTLY TO USER
        # ----------------------------------------------------

        response = HttpResponse(

            output.getvalue(),

            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

        response[
            "Content-Disposition"
        ] = (
            f'attachment; filename="{safe_filename}"'
        )

        # ----------------------------------------------------
        # CLEAN CACHE AFTER DOWNLOAD
        # ----------------------------------------------------

        delete_cleaned_dataset(
            dataset_id
        )

        delete_stored_dataset(
            dataset_id
        )

        # Remove session references
        request.session.pop(
            "cleaned_filename",
            None,
        )

        request.session.pop(
            "dataset_id",
            None,
        )

        request.session.pop(
            "dataset_filename",
            None,
        )

        return response

    except Exception as e:

        traceback.print_exc()

        raise Http404(
            "Unable to generate the cleaned Excel file."
        )


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_required(view_func):
    """
    Allow access only to authenticated staff users.
    """

    return user_passes_test(
        lambda user:
            user.is_authenticated
            and user.is_staff,
        login_url="/login/",
    )(view_func)


# ============================================================
# PUBLIC BLOG LIST
# ============================================================

def blog_list(request):

    posts = (
        BlogPost.objects
        .all()
        .order_by("-created_at")
    )

    search_query = request.GET.get(
        "q",
        "",
    ).strip()

    if search_query:

        posts = (
            posts.filter(
                title__icontains=search_query
            )
            |
            posts.filter(
                content__icontains=search_query
            )
        )

    return render(
        request,
        "blog.html",
        {
            "posts":
                posts,

            "search_query":
                search_query,
        },
    )


# ============================================================
# BLOG DETAIL
# ============================================================

def blog_detail(
    request,
    slug,
):

    post = get_object_or_404(
        BlogPost,
        slug=slug,
    )

    return render(
        request,
        "blog_detail.html",
        {
            "post":
                post,
        },
    )


# ============================================================
# ADMIN BLOG DASHBOARD
# ============================================================

@admin_required
def blog_admin_dashboard(request):

    posts = (
        BlogPost.objects
        .all()
        .order_by("-created_at")
    )

    return render(
        request,
        "admin/dashboard.html",
        {
            "posts":
                posts,

            "total_posts":
                posts.count(),
        },
    )


# ============================================================
# CREATE BLOG POST
# ============================================================

@admin_required
def blog_create(request):

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "",
        ).strip()

        content = request.POST.get(
            "content",
            "",
        ).strip()

        excerpt = request.POST.get(
            "excerpt",
            "",
        ).strip()

        featured_image = request.FILES.get(
            "featured_image"
        )

        if not title:

            messages.error(
                request,
                "Blog title is required.",
            )

            return render(
                request,
                "admin/blog_form.html",
                {
                    "action":
                        "Create",
                },
            )

        if not content:

            messages.error(
                request,
                "Blog content is required.",
            )

            return render(
                request,
                "admin/blog_form.html",
                {
                    "action":
                        "Create",
                },
            )

        base_slug = slugify(
            title
        )

        slug = base_slug

        counter = 1

        while BlogPost.objects.filter(
            slug=slug
        ).exists():

            slug = (
                f"{base_slug}-{counter}"
            )

            counter += 1

        BlogPost.objects.create(

            title=title,

            slug=slug,

            excerpt=excerpt,

            content=content,

            featured_image=featured_image,
        )

        messages.success(
            request,
            "Blog post published successfully.",
        )

        return redirect(
            "blog_admin_dashboard"
        )

    return render(
        request,
        "admin/blog_form.html",
        {
            "action":
                "Create",
        },
    )


# ============================================================
# EDIT BLOG POST
# ============================================================

@admin_required
def blog_edit(
    request,
    pk,
):

    post = get_object_or_404(
        BlogPost,
        pk=pk,
    )

    if request.method == "POST":

        title = request.POST.get(
            "title",
            "",
        ).strip()

        content = request.POST.get(
            "content",
            "",
        ).strip()

        excerpt = request.POST.get(
            "excerpt",
            "",
        ).strip()

        featured_image = request.FILES.get(
            "featured_image"
        )

        if not title:

            messages.error(
                request,
                "Blog title is required.",
            )

            return render(
                request,
                "admin/blog_form.html",
                {
                    "post":
                        post,

                    "action":
                        "Edit",
                },
            )

        if not content:

            messages.error(
                request,
                "Blog content is required.",
            )

            return render(
                request,
                "admin/blog_form.html",
                {
                    "post":
                        post,

                    "action":
                        "Edit",
                },
            )

        if post.title != title:

            base_slug = slugify(
                title
            )

            slug = base_slug

            counter = 1

            while (
                BlogPost.objects
                .filter(
                    slug=slug
                )
                .exclude(
                    pk=post.pk
                )
                .exists()
            ):

                slug = (
                    f"{base_slug}-{counter}"
                )

                counter += 1

            post.slug = slug

        post.title = title

        post.excerpt = excerpt

        post.content = content

        if featured_image:

            post.featured_image = featured_image

        post.save()

        messages.success(
            request,
            "Blog post updated successfully.",
        )

        return redirect(
            "blog_admin_dashboard"
        )

    return render(
        request,
        "admin/blog_form.html",
        {
            "post":
                post,

            "action":
                "Edit",
        },
    )


# ============================================================
# DELETE BLOG POST
# ============================================================

@admin_required
def blog_delete(
    request,
    pk,
):

    post = get_object_or_404(
        BlogPost,
        pk=pk,
    )

    if request.method == "POST":

        post.delete()

        messages.success(
            request,
            "Blog post deleted successfully.",
        )

        return redirect(
            "blog_admin_dashboard"
        )

    return render(
        request,
        "admin/blog_delete.html",
        {
            "post":
                post,
        },
    )


# ============================================================
# PAYMENT CALLBACK
# ============================================================

@login_required
def payment_callback(request):

    reference = request.GET.get(
        "reference"
    )

    if not reference:

        messages.error(
            request,
            "Payment reference was not provided.",
        )

        return redirect(
            "pricing"
        )

    # ========================================================
    # FIND PAYMENT
    # ========================================================

    payment = get_object_or_404(
        Payment,
        reference=reference,
    )

    if payment.status == "success":

        messages.success(
            request,
            "Your payment has already been processed.",
        )

        return redirect(
            "dashboard"
        )

    # ========================================================
    # VERIFY PAYMENT WITH PAYSTACK
    # ========================================================

    url = (
        "https://api.paystack.co/"
        "transaction/verify/"
        f"{reference}"
    )

    headers = {

        "Authorization":
            f"Bearer {settings.PAYSTACK_SECRET_KEY}",

        "Content-Type":
            "application/json",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        result = response.json()

    except requests.RequestException:

        messages.error(
            request,
            "Unable to verify your payment.",
        )

        return redirect(
            "pricing"
        )

    # ========================================================
    # CHECK PAYSTACK RESPONSE
    # ========================================================

    if (
        result.get("status") is not True
        or
        result.get(
            "data",
            {}
        ).get(
            "status"
        ) != "success"
    ):

        payment.status = "failed"

        payment.save(
            update_fields=[
                "status"
            ]
        )

        messages.error(
            request,
            "Payment was not successful.",
        )

        return redirect(
            "pricing"
        )

    # ========================================================
    # GET PLAN
    # ========================================================

    plan = get_object_or_404(
        SubscriptionPlan,
        name=payment.plan_name,
        is_active=True,
    )

    # ========================================================
    # CONFIRM AMOUNT
    # ========================================================

    paystack_amount = (
        result["data"].get(
            "amount"
        )
    )

    expected_amount = int(
        payment.amount * 100
    )

    if paystack_amount != expected_amount:

        payment.status = "failed"

        payment.save(
            update_fields=[
                "status"
            ]
        )

        messages.error(
            request,
            "Payment amount verification failed.",
        )

        return redirect(
            "pricing"
        )

    # ========================================================
    # MARK PAYMENT SUCCESSFUL
    # ========================================================

    now = timezone.now()

    payment.status = "success"

    payment.paid_at = now

    payment.save(
        update_fields=[
            "status",
            "paid_at",
        ]
    )

    # ========================================================
    # EXPIRE EXISTING ACTIVE SUBSCRIPTIONS
    # ========================================================

    Subscription.objects.filter(
        user=payment.user,
        status="active",
    ).update(
        status="expired"
    )

    # ========================================================
    # CREATE NEW SUBSCRIPTION
    # ========================================================

    subscription = Subscription.objects.create(

        user=payment.user,

        plan=plan,

        payment_reference=payment.reference,

        status="active",

        starts_at=now,

        expires_at=(
            now
            +
            timedelta(
                days=plan.duration_days
            )
        ),
    )

    # ========================================================
    # LINK PAYMENT TO SUBSCRIPTION
    # ========================================================

    payment.subscription = subscription

    payment.save(
        update_fields=[
            "subscription"
        ]
    )

    # ========================================================
    # SUCCESS
    # ========================================================

    messages.success(
        request,
        (
            f"Payment successful! "
            f"Your {plan.get_name_display()} "
            f"plan is now active."
        ),
    )

    return redirect(
        "dashboard"
    )


# ============================================================
# HANDLE MISSING VALUES
# ============================================================

def handle_missing_values(
    df,
    replacement="",
):
    """
    Replace missing values safely.

    Numeric input into numeric columns remains numeric.
    Text such as UNKNOWN automatically converts the column
    so both numbers and text can coexist.
    """

    df = df.copy()

    if replacement is None:

        return df

    replacement = str(
        replacement
    )

    for column in df.columns:

        if not df[column].isna().any():

            continue

        dtype = df[column].dtype

        # ====================================================
        # NUMERIC COLUMN
        # ====================================================

        if pd.api.types.is_numeric_dtype(
            dtype
        ):

            try:

                numeric_value = pd.to_numeric(
                    replacement
                )

                if pd.api.types.is_integer_dtype(
                    dtype
                ):

                    if float(
                        numeric_value
                    ).is_integer():

                        df[column] = (
                            df[column]
                            .fillna(
                                int(
                                    numeric_value
                                )
                            )
                        )

                    else:

                        df[column] = (
                            df[column]
                            .astype(object)
                        )

                        df.loc[
                            df[column].isna(),
                            column
                        ] = replacement

                else:

                    df[column] = (
                        df[column]
                        .fillna(
                            float(
                                numeric_value
                            )
                        )
                    )

            except (
                ValueError,
                TypeError,
            ):

                df[column] = (
                    df[column]
                    .astype(object)
                )

                missing_mask = (
                    df[column]
                    .isna()
                )

                df.loc[
                    missing_mask,
                    column
                ] = replacement

        # ====================================================
        # DATETIME COLUMN
        # ====================================================

        elif pd.api.types.is_datetime64_any_dtype(
            dtype
        ):

            try:

                date_value = pd.to_datetime(
                    replacement
                )

                df[column] = (
                    df[column]
                    .fillna(
                        date_value
                    )
                )

            except (
                ValueError,
                TypeError,
            ):

                df[column] = (
                    df[column]
                    .astype(object)
                )

                missing_mask = (
                    df[column]
                    .isna()
                )

                df.loc[
                    missing_mask,
                    column
                ] = replacement

        # ====================================================
        # BOOLEAN COLUMN
        # ====================================================

        elif pd.api.types.is_bool_dtype(
            dtype
        ):

            value = (
                replacement
                .strip()
                .lower()
            )

            if value in (
                "true",
                "yes",
                "1",
            ):

                df[column] = (
                    df[column]
                    .fillna(True)
                )

            elif value in (
                "false",
                "no",
                "0",
            ):

                df[column] = (
                    df[column]
                    .fillna(False)
                )

            else:

                df[column] = (
                    df[column]
                    .astype(object)
                )

                missing_mask = (
                    df[column]
                    .isna()
                )

                df.loc[
                    missing_mask,
                    column
                ] = replacement

        # ====================================================
        # TEXT / OBJECT COLUMN
        # ====================================================

        else:

            df[column] = (
                df[column]
                .fillna(
                    replacement
                )
            )

    return df









# ============================================================
# FREE DATA QUALITY CHECK
# ============================================================

def quality_check(request):

    if request.method == "GET":

        return render(
            request,
            "quality_check.html"
        )

    uploaded_file = request.FILES.get("file")

    if not uploaded_file:

        messages.error(
            request,
            "Please select an Excel or CSV file."
        )

        return redirect("quality_check")


    # --------------------------------------------------------
    # FILE EXTENSION
    # --------------------------------------------------------

    filename = uploaded_file.name

    suffix = Path(
        filename
    ).suffix.lower()


    allowed_extensions = (
        ".csv",
        ".xlsx",
        ".xls",
    )


    if suffix not in allowed_extensions:

        messages.error(
            request,
            "Only CSV and Excel files are supported."
        )

        return redirect("quality_check")


    # --------------------------------------------------------
    # FREE TOOL SIZE LIMIT
    # --------------------------------------------------------

    max_size = 10 * 1024 * 1024

    if uploaded_file.size > max_size:

        messages.error(
            request,
            "The free quality checker supports files up to 10 MB."
        )

        return redirect("quality_check")


    temp_path = None


    try:

        # ----------------------------------------------------
        # SAVE TEMPORARY FILE
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False
        ) as temp_file:

            for chunk in uploaded_file.chunks():

                temp_file.write(chunk)

            temp_path = temp_file.name


        # ----------------------------------------------------
        # READ FILE
        # ----------------------------------------------------

        df = read_file(
            Path(temp_path),
            filename
        )


        if df is None:

            raise ValueError(
                "Unable to read the uploaded file."
            )


        # ----------------------------------------------------
        # ANALYZE
        # ----------------------------------------------------

        analysis = analyze_dataframe(
            df
        )


        # ----------------------------------------------------
        # CALCULATE QUALITY SCORE
        # ----------------------------------------------------

        total_rows = analysis.get(
            "total_rows",
            0
        )

        total_columns = analysis.get(
            "total_columns",
            0
        )

        missing_cells = analysis.get(
            "missing_cells",
            0
        )

        blank_cells = analysis.get(
            "blank_cells",
            0
        )

        duplicate_rows = analysis.get(
            "duplicate_rows",
            0
        )

        empty_rows = analysis.get(
            "empty_rows",
            0
        )

        empty_columns = analysis.get(
            "empty_columns",
            0
        )


        total_cells = (
            total_rows *
            total_columns
        )


        # ----------------------------------------------------
        # COMPLETENESS
        # ----------------------------------------------------

        if total_cells > 0:

            completeness = (
                (
                    total_cells -
                    missing_cells -
                    empty_rows
                )
                /
                total_cells
            ) * 100

        else:

            completeness = 100


        completeness = max(
            0,
            min(
                100,
                round(completeness, 1)
            )
        )


        # ----------------------------------------------------
        # DUPLICATE PERCENTAGE
        # ----------------------------------------------------

        if total_rows > 0:

            duplicate_percentage = round(
                (
                    duplicate_rows /
                    total_rows
                ) * 100,
                1
            )

        else:

            duplicate_percentage = 0


        # ----------------------------------------------------
        # QUALITY SCORE
        # ----------------------------------------------------

        quality_score = completeness


        if duplicate_percentage > 0:

            quality_score -= min(
                duplicate_percentage,
                20
            )


        if empty_columns > 0 and total_columns > 0:

            empty_column_percentage = (
                empty_columns /
                total_columns
            ) * 100

            quality_score -= min(
                empty_column_percentage,
                10
            )


        quality_score = max(
            0,
            min(
                100,
                round(quality_score)
            )
        )


        # ----------------------------------------------------
        # QUALITY STATUS
        # ----------------------------------------------------

        if quality_score >= 90:

            quality_status = "Excellent"

            quality_class = "success"

        elif quality_score >= 75:

            quality_status = "Good"

            quality_class = "primary"

        elif quality_score >= 50:

            quality_status = "Needs Improvement"

            quality_class = "warning"

        else:

            quality_status = "Poor"

            quality_class = "danger"


        # ----------------------------------------------------
        # COLUMN ANALYSIS
        # ----------------------------------------------------

        columns = analysis.get(
            "columns",
            []
        )


        # ----------------------------------------------------
        # RENDER RESULTS
        # ----------------------------------------------------

        return render(
            request,
            "quality_check.html",
            {
                "filename": filename,

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

                "completeness":
                    completeness,

                "duplicate_percentage":
                    duplicate_percentage,

                "quality_score":
                    quality_score,

                "quality_status":
                    quality_status,

                "quality_class":
                    quality_class,

                "columns":
                    columns,

                "checked":
                    True,
            }
        )


    except Exception as e:

        messages.error(
            request,
            f"Unable to analyze the uploaded file: {str(e)}"
        )

        return redirect(
            "quality_check"
        )


    finally:

        # ----------------------------------------------------
        # DELETE TEMPORARY FILE
        # ----------------------------------------------------

        if temp_path:

            try:

                os.unlink(
                    temp_path
                )

            except OSError:

                pass