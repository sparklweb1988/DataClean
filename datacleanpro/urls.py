from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin

from django.urls import path, include


urlpatterns = [

    # ========================================================
    # DJANGO ADMIN
    # ========================================================

    path(
        "admin/",
        admin.site.urls
    ),


    # ========================================================
    # CORE APPLICATION
    #
    # All DataClean Pro functionality lives inside
    # the core app.
    # ========================================================

    path(
        "",
        include("core.urls")
    ),

]


# ============================================================
# DEVELOPMENT MEDIA FILES
# ============================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )