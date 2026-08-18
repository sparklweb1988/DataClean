from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone


# ============================================================
# SUBSCRIPTION PLANS
# ============================================================

class SubscriptionPlan(models.Model):

    PLAN_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("pro", "Pro"),
        ("business", "Business"),
    ]

    name = models.CharField(
        max_length=50,
        choices=PLAN_CHOICES,
        unique=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    duration_days = models.PositiveIntegerField(
        default=30
    )

    max_rows = models.PositiveIntegerField(
        default=1000
    )

    max_columns = models.PositiveIntegerField(
        default=30
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return self.get_name_display()
# ============================================================
# USER SUBSCRIPTIONS
# ============================================================

class Subscription(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("pending", "Pending"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    payment_reference = models.CharField(
        max_length=255,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active"
    )

    starts_at = models.DateTimeField(
        default=timezone.now
    )

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

    @property
    def is_active(self):
        return (
            self.status == "active"
            and self.expires_at > timezone.now()
        )

# ============================================================
# PAYMENTS
# ============================================================

class Payment(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments"
    )

    reference = models.CharField(
        max_length=255,
        unique=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default="NGN"
    )

    plan_name = models.CharField(
        max_length=50
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} - ₦{self.amount}"


# ============================================================
# DATASET
# ============================================================

class Dataset(models.Model):

    FILE_TYPE_CHOICES = [
        ("csv", "CSV"),
        ("xlsx", "Excel"),
        ("xls", "Excel"),
    ]

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("analyzed", "Analyzed"),
        ("cleaned", "Cleaned"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="datasets"
    )

    original_filename = models.CharField(
        max_length=255
    )

    file = models.FileField(
        upload_to="datasets/original/"
    )

    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES
    )

    total_rows = models.PositiveIntegerField(
        default=0
    )

    total_columns = models.PositiveIntegerField(
        default=0
    )

    duplicate_rows = models.PositiveIntegerField(
        default=0
    )

    blank_cells = models.PositiveIntegerField(
        default=0
    )

    missing_values = models.PositiveIntegerField(
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="uploaded"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_filename


# ============================================================
# CLEANED DATASET
# ============================================================

class CleanedDataset(models.Model):

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="cleaned_files"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cleaned_datasets"
    )

    file = models.FileField(
        upload_to="datasets/cleaned/"
    )

    filename = models.CharField(
        max_length=255
    )

    rows_before = models.PositiveIntegerField(
        default=0
    )

    rows_after = models.PositiveIntegerField(
        default=0
    )

    columns_before = models.PositiveIntegerField(
        default=0
    )

    columns_after = models.PositiveIntegerField(
        default=0
    )

    duplicates_removed = models.PositiveIntegerField(
        default=0
    )

    missing_values_replaced = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename


# ============================================================
# DATA CLEANING ACTIVITY
# ============================================================

class CleaningActivity(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cleaning_activities"
    )

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    action = models.CharField(
        max_length=100
    )

    rows_processed = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.action}"
        )


# ============================================================
# BLOG CATEGORY
# ============================================================

class BlogCategory(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name_plural = "Blog Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ============================================================
# BLOG POST
# ============================================================

class BlogPost(models.Model):

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blog_posts"
    )

    

    title = models.CharField(
        max_length=255
    )

    slug = models.SlugField(
        max_length=280,
        unique=True,
        blank=True
    )

    excerpt = models.TextField(
        blank=True
    )

    content = models.TextField()


    meta_title = models.CharField(
        max_length=255,
        blank=True
    )

    meta_description = models.TextField(
        blank=True
    )

    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Separate tags with commas."
    )

    views = models.PositiveIntegerField(
        default=0
    )

    is_published = models.BooleanField(
        default=True
    )

    published_at = models.DateTimeField(
        default=timezone.now
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-published_at"]

    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(
                self.title
            )

            slug = base_slug

            counter = 1

            while BlogPost.objects.filter(
                slug=slug
            ).exclude(
                pk=self.pk
            ).exists():

                slug = (
                    f"{base_slug}-"
                    f"{counter}"
                )

                counter += 1

            self.slug = slug

        if not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def tag_list(self):

        if not self.tags:
            return []

        return [
            tag.strip()
            for tag in self.tags.split(",")
            if tag.strip()
        ]


# ============================================================
# BLOG COMMENT
# ============================================================

class BlogComment(models.Model):

    post = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    name = models.CharField(
        max_length=100
    )

    email = models.EmailField()

    comment = models.TextField()

    is_approved = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.name} - "
            f"{self.post.title}"
        )