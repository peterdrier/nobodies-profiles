"""
Custom User model for Nobodies Profiles.

CRITICAL: This model must exist before running any migrations.
The User model uses email as the primary identifier (no username).
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, display_name='', password=None, **extra_fields):
        """Create and return a regular user with the given email."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, display_name=display_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, display_name='', password=None, **extra_fields):
        """Create and return a superuser with the given email."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, display_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with email as the unique identifier.

    Authentication is via Google OAuth only (no username/password for regular users).
    The email field is the user's Google account email.
    """

    LANGUAGE_CHOICES = [
        ('es', _('Spanish')),
        ('en', _('English')),
        ('fr', _('French')),
        ('de', _('German')),
        ('pt', _('Portuguese')),
    ]

    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_('Google account email address'),
    )
    display_name = models.CharField(
        _('display name'),
        max_length=255,
        blank=True,
        help_text=_('Name shown in the UI'),
    )
    preferred_language = models.CharField(
        _('preferred language'),
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text=_('Language for emails and UI'),
    )
    date_joined = models.DateTimeField(
        _('date joined'),
        default=timezone.now,
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this user can log in.'),
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can access the admin site.'),
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the display name or email if not set."""
        return self.display_name or self.email

    def get_short_name(self):
        """Return the display name or email if not set."""
        return self.display_name or self.email.split('@')[0]
