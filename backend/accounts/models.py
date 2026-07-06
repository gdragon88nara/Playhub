"""
Accounts domain.

Design notes
------------
* Login identity is the email address; ``username`` is the public @handle
  (Instagram-style).
* Account privacy: ``is_private``. Public accounts expose their games/posts to
  everyone; private accounts only to accepted followers.
* Sellers: any user can additionally become a seller. We store **no** raw
  financial data (no card / bank / national-id numbers). Only a reference to
  the payment provider's onboarded account (e.g. a Stripe Connect account id)
  plus onboarding status. This keeps us out of PCI/KYC scope by delegation.
* Follow graph: a directed ``Follow`` edge (follower -> following). Following a
  private account first creates a ``FollowRequest``; on accept we create the
  edge AND an automatic reverse edge (mutual follow) per product requirement.
"""

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils import timezone


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, username, password, **extra):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, username, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, username, password, **extra)

    def create_superuser(self, email, username, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra["is_staff"] is not True or extra["is_superuser"] is not True:
            raise ValueError("Superuser must have is_staff and is_superuser=True")
        return self._create_user(email, username, password, **extra)


handle_validator = RegexValidator(
    regex=r"^[a-zA-Z0-9._]+$",
    message="Handle may contain letters, numbers, dot and underscore only.",
)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=30, unique=True, validators=[handle_validator],
        help_text="Public @handle.",
    )
    display_name = models.CharField(max_length=60, blank=True)
    bio = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    is_private = models.BooleanField(
        default=False,
        help_text="Private accounts only reveal content to accepted followers.",
    )
    is_seller = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    # Coarse "last seen" — refreshed (throttled) when the user loads their profile.
    last_active = models.DateTimeField(null=True, blank=True)

    # Notification preferences (which activity generates a notification).
    notify_follows = models.BooleanField(default=True)
    notify_likes = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        indexes = [models.Index(fields=["username"])]

    def __str__(self):
        return f"@{self.username}"

    # -- follow graph helpers ------------------------------------------------
    @property
    def followers_count(self):
        return self.follower_edges.count()

    @property
    def following_count(self):
        return self.following_edges.count()

    def is_following(self, other) -> bool:
        return Follow.objects.filter(follower=self, following=other).exists()

    def can_view_content(self, viewer) -> bool:
        """Whether ``viewer`` may see this user's games/posts."""
        if not self.is_private:
            return True
        if viewer is None or not viewer.is_authenticated:
            return False
        if viewer.pk == self.pk:
            return True
        return Follow.objects.filter(follower=viewer, following=self).exists()


# ---------------------------------------------------------------------------
# Seller profile  (no raw financial data — provider references only)
# ---------------------------------------------------------------------------
class SellerProfile(models.Model):
    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe Connect"
        PORTONE = "portone", "PortOne"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending onboarding"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        DISABLED = "disabled", "Disabled"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_profile"
    )
    business_display_name = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=2, blank=True, help_text="ISO 3166-1 alpha-2")

    provider = models.CharField(max_length=16, choices=Provider.choices, blank=True)
    # Opaque reference to the provider-hosted connected account. NOT a bank
    # number, card, or any PII we are liable for. Populated after the user
    # completes the provider's hosted onboarding flow.
    provider_account_id = models.CharField(max_length=255, blank=True)

    onboarding_status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    payouts_enabled = models.BooleanField(default=False)

    # Platform commission withheld on each sale (default 20%).
    commission_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=0.20
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SellerProfile(@{self.user.username}, {self.onboarding_status})"


# ---------------------------------------------------------------------------
# Follow graph
# ---------------------------------------------------------------------------
class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_edges"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_edges"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"], name="uniq_follow_edge"
            ),
            models.CheckConstraint(
                check=~models.Q(follower=models.F("following")),
                name="no_self_follow",
            ),
        ]
        indexes = [
            models.Index(fields=["follower"]),
            models.Index(fields=["following"]),
        ]

    def __str__(self):
        return f"@{self.follower.username} -> @{self.following.username}"


class FollowRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_follow_requests"
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_follow_requests"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["requester", "target"],
                condition=models.Q(status="pending"),
                name="uniq_pending_follow_request",
            ),
        ]

    def __str__(self):
        return f"req @{self.requester.username} -> @{self.target.username} ({self.status})"

    @transaction.atomic
    def accept(self):
        """Accept the request: create the edge AND the automatic reverse edge.

        Product rule: when the target accepts, the target also auto-follows the
        requester back (mutual follow) with no separate request — even for
        private accounts.
        """
        self.status = self.Status.ACCEPTED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])
        Follow.objects.get_or_create(follower=self.requester, following=self.target)
        Follow.objects.get_or_create(follower=self.target, following=self.requester)

    def reject(self):
        self.status = self.Status.REJECTED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at"])


# ---------------------------------------------------------------------------
# Safety: blocking & reporting
# ---------------------------------------------------------------------------
class Block(models.Model):
    """``blocker`` no longer wants to see or be contacted by ``blocked``."""

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocking"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocked_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="uniq_block"),
            models.CheckConstraint(
                check=~models.Q(blocker=models.F("blocked")), name="no_self_block"
            ),
        ]

    def __str__(self):
        return f"@{self.blocker.username} blocks @{self.blocked.username}"


class Report(models.Model):
    """A user-submitted abuse/safety report. Reviewed by staff out of band."""

    class Kind(models.TextChoices):
        USER = "user", "User"
        GAME = "game", "Game"
        POST = "post", "Post"
        COMMENT = "comment", "Comment"
        OTHER = "other", "Other"

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        ABUSE = "abuse", "Abuse or harassment"
        HATE = "hate", "Hate speech"
        SEXUAL = "sexual", "Sexual or explicit content"
        ILLEGAL = "illegal", "Illegal or dangerous"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        REVIEWED = "reviewed", "Reviewed"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.OTHER)
    # A free-form reference to the reported thing (a @handle, game slug, url…).
    target = models.CharField(max_length=255, blank=True)
    reason = models.CharField(max_length=10, choices=Reason.choices, default=Reason.OTHER)
    note = models.CharField(max_length=1000, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report({self.kind}:{self.target}) by @{self.reporter.username}"
