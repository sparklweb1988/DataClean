from django.contrib import admin

from .models import (
    SubscriptionPlan,
    Subscription,
    Payment,
    Dataset,
    CleanedDataset,
    CleaningActivity,
    BlogCategory,
    BlogPost,
    BlogComment,
)


# ============================================================
# SUBSCRIPTION PLAN
# ============================================================

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "price",
        "duration_days",
        "max_rows",
        "is_active",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "name",
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    ordering = (
        "price",
    )

    list_editable = (
        "price",
        "duration_days",
        "max_rows",
        "is_active",
    )


# ============================================================
# SUBSCRIPTION
# ============================================================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "plan",
        "status",
        "starts_at",
        "expires_at",
        "is_active_status",
        "created_at",
    )

    list_filter = (
        "status",
        "plan",
        "starts_at",
        "expires_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "payment_reference",
        "plan__name",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "user",
        "plan",
    )

    def is_active_status(self, obj):
        return obj.is_active

    is_active_status.boolean = True
    is_active_status.short_description = "Active"


# ============================================================
# PAYMENT
# ============================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "reference",
        "user",
        "amount",
        "currency",
        "plan_name",
        "status",
        "paid_at",
        "created_at",
    )

    list_filter = (
        "status",
        "currency",
        "plan_name",
        "paid_at",
        "created_at",
    )

    search_fields = (
        "reference",
        "user__username",
        "user__email",
        "plan_name",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "user",
        "subscription",
    )


# ============================================================
# DATASET
# ============================================================

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):

    list_display = (
        "original_filename",
        "user",
        "file_type",
        "total_rows",
        "total_columns",
        "duplicate_rows",
        "blank_cells",
        "missing_values",
        "status",
        "uploaded_at",
    )

    list_filter = (
        "file_type",
        "status",
        "uploaded_at",
    )

    search_fields = (
        "original_filename",
        "user__username",
        "user__email",
    )

    ordering = (
        "-uploaded_at",
    )

    readonly_fields = (
        "uploaded_at",
        "updated_at",
    )

    autocomplete_fields = (
        "user",
    )


# ============================================================
# CLEANED DATASET
# ============================================================

@admin.register(CleanedDataset)
class CleanedDatasetAdmin(admin.ModelAdmin):

    list_display = (
        "filename",
        "user",
        "dataset",
        "rows_before",
        "rows_after",
        "columns_before",
        "columns_after",
        "duplicates_removed",
        "missing_values_replaced",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "filename",
        "user__username",
        "user__email",
        "dataset__original_filename",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
    )

    autocomplete_fields = (
        "user",
        "dataset",
    )


# ============================================================
# CLEANING ACTIVITY
# ============================================================

@admin.register(CleaningActivity)
class CleaningActivityAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "dataset",
        "action",
        "rows_processed",
        "created_at",
    )

    list_filter = (
        "action",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "dataset__original_filename",
        "action",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
    )

    autocomplete_fields = (
        "user",
        "dataset",
    )


# ============================================================
# BLOG CATEGORY
# ============================================================

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "created_at",
    )

    search_fields = (
        "name",
        "slug",
        "description",
    )

    ordering = (
        "name",
    )

    readonly_fields = (
        "created_at",
    )


# ============================================================
# BLOG POST
# ============================================================

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "author",
     
        "is_published",
        "views",
        "published_at",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_published",
      
        "published_at",
        "created_at",
    )

    search_fields = (
        "title",
        "slug",
        "excerpt",
        "content",
        "meta_title",
        "meta_description",
        "tags",
        "author__username",
    )

    ordering = (
        "-published_at",
    )

    readonly_fields = (

        "views",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "author",
    
    )

    prepopulated_fields = {
        "slug": ("title",),
    }

    fieldsets = (

        (
            "Post Information",
            {
                "fields": (
                    "title",
                    "slug",
                    "author",
                    "category",
                   
                    "excerpt",
                    "content",
                    "tags",
                )
            }
        ),

        (
            "SEO",
            {
                "fields": (
                    "meta_title",
                    "meta_description",
                )
            }
        ),

        (
            "Publishing",
            {
                "fields": (
                    "is_published",
                    "published_at",
                )
            }
        ),

        (
            "Statistics",
            {
                "fields": (
                    "views",
                    "created_at",
                    "updated_at",
                )
            }
        ),
    )


# ============================================================
# BLOG COMMENT
# ============================================================

@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "email",
        "post",
        "is_approved",
        "created_at",
    )

    list_filter = (
        "is_approved",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "comment",
        "post__title",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
    )

    autocomplete_fields = (
        "post",
    )