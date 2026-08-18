from django.urls import path

from . import views


urlpatterns = [

    # ========================================================
    # PUBLIC PAGES
    # ========================================================

    path(
        "",
        views.home,
        name="home",
    ),

    path(
        "about/",
        views.about,
        name="about",
    ),

    path(
        "contact/",
        views.contact,
        name="contact",
    ),

    path(
        "privacy/",
        views.privacy,
        name="privacy",
    ),


    # ========================================================
    # AUTHENTICATION
    # ========================================================

    path(
        "register/",
        views.register,
        name="register",
    ),

    path(
        "login/",
        views.login_view,
        name="login",
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),


    # ========================================================
    # PRICING
    # ========================================================

    path(
        "pricing/",
        views.pricing,
        name="pricing",
    ),

    # ========================================================
# FREE PLAN
# ========================================================

        path(
            "payments/free/",
            views.activate_free_plan,
            name="activate_free_plan",
        ),

    # ========================================================
    # DASHBOARD
    # ========================================================

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),


    # ========================================================
    # PAYMENTS
    # ========================================================

    path(
        "payments/initialize/",
        views.initialize_payment,
        name="initialize_payment",
    ),

    path(
        "payments/callback/",
        views.payment_callback,
        name="payment_callback",
    ),


    # ========================================================
    # DATA CLEANER
    # ========================================================

    path(
        "upload/",
        views.upload_page,
        name="upload",
    ),

    path(
        "upload/process/",
        views.upload_dataset,
        name="upload_dataset",
    ),

    path(
    "clean_dataset/",
    views.clean_dataset,
    name="clean_dataset",
    ),

    path(
        "download/<str:filename>/",
        views.download_file,
        name="download_file",
    ),


    # ========================================================
    # BLOG - PUBLIC
    # ========================================================

    path(
        "blog/",
        views.blog_list,
        name="blog_list",
    ),

    path(
        "blog/<slug:slug>/",
        views.blog_detail,
        name="blog_detail",
    ),


    # ========================================================
    # BLOG - ADMIN DASHBOARD
    # ========================================================

    path(
        "admin-dashboard/blog/",
        views.blog_admin_dashboard,
        name="blog_admin_dashboard",
    ),


    # ========================================================
    # BLOG - CREATE
    # ========================================================

    path(
        "admin-dashboard/blog/create/",
        views.blog_create,
        name="blog_create",
    ),


    # ========================================================
    # BLOG - EDIT
    # ========================================================

    path(
        "admin-dashboard/blog/<int:pk>/edit/",
        views.blog_edit,
        name="blog_edit",
    ),


    # ========================================================
    # BLOG - DELETE
    # ========================================================

    path(
        "admin-dashboard/blog/<int:pk>/delete/",
        views.blog_delete,
        name="blog_delete",
    ),





    path(
    "quality-check/",
    views.quality_check,
    name="quality_check",
),


]
