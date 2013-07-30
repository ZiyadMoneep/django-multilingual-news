"""Models for the ``multilingual_news`` app."""
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _

from cms.models import CMSPlugin
from cms.utils import get_language_from_request
from django_libs.models_mixins import SimpleTranslationMixin
from djangocms_utils.fields import M2MPlaceholderField
from filer.fields.image import FilerImageField
from simple_translation.actions import SimpleTranslationPlaceholderActions
from simple_translation.utils import get_preferred_translation_from_lang
from simple_translation.utils import get_translation_filter_language


class NewsEntryManager(models.Manager):
    """Custom manager for the ``NewsEntry`` model."""
    def published(self, request, check_language=True):
        """
        Returns all entries, which publication date has been hit or which have
        no date and which language matches the current language.

        :param request: A Request instance.
        :param check_language: Option to disable language filtering.

        """
        qs = self.get_query_set().filter(
            models.Q(newsentrytitle__is_published=True),
            models.Q(pub_date__lte=now()) | models.Q(pub_date__isnull=True)
        )
        if check_language:
            language = get_language_from_request(request)
            kwargs = get_translation_filter_language(NewsEntry, language)
            qs = qs.filter(**kwargs)
        return qs.distinct()

    def recent(self, request, check_language=True, limit=3, exclude=None):
        """
        Returns recently published new entries.

        :param request: A Request instance.
        :param check_language: Option to disable language filtering.

        """
        qs = self.published(request, check_language=check_language)
        if check_language:
            # Filter news with current language
            language = get_language_from_request(request)
            kwargs = get_translation_filter_language(NewsEntry, language)
            qs = qs.filter(**kwargs)
        if exclude:
            qs = qs.exclude(pk=exclude.pk)
        return qs[:limit]


class NewsEntry(SimpleTranslationMixin, models.Model):
    """
    A news entry consists of a title, content and media fields.

    See ``NewsEntryTitle`` for the translateable fields of this model.

    :author: Optional FK to the User who created this entry.
    :pub_date: DateTime when this entry should be published.
    :image: Main image of the blog entry.
    :image_float: Can be set to ``none``, ``left`` or ``right`` to adjust
      floating behaviour in the blog entry template.
    :image_width: Can be set to manipulate image width
    :image_height: Can be set to manipulate image height
    :image_source_text: Text for the link to the image source
    :image_source_url: URL for the link to the image source
    :placeholders: CMS placeholders for ``exerpt`` and ``content``

    """
    IMAGE_FLOAT_VALUES = {
        'left': 'left',
        'right': 'right',
    }

    IMAGE_FLOAT_CHOICES = (
        (IMAGE_FLOAT_VALUES['left'], _('Left')),
        (IMAGE_FLOAT_VALUES['right'], _('Right')),
    )

    author = models.ForeignKey(
        'auth.User',
        verbose_name=_('Author'),
        null=True, blank=True,
    )

    pub_date = models.DateTimeField(
        verbose_name=_('Publication date'),
        blank=True, null=True,
    )

    image = FilerImageField(
        verbose_name=_('Image'),
        null=True, blank=True,
    )

    image_float = models.CharField(
        max_length=8,
        verbose_name=_('Image float'),
        choices=IMAGE_FLOAT_CHOICES,
        blank=True,
    )

    image_width = models.IntegerField(
        verbose_name=_('Image width'),
        null=True, blank=True,
    )

    image_height = models.IntegerField(
        verbose_name=_('Image height'),
        null=True, blank=True,
    )

    image_source_url = models.CharField(
        max_length=1024,
        verbose_name=_('Image source URL'),
        blank=True,
    )

    image_source_text = models.CharField(
        max_length=1024,
        verbose_name=_('Image source text'),
        blank=True,
    )

    placeholders = M2MPlaceholderField(
        actions=SimpleTranslationPlaceholderActions(),
        placeholders=('excerpt', 'content'),
    )

    objects = NewsEntryManager()

    class Meta:
        ordering = ('-pub_date', )

    def __unicode__(self):
        return self.get_title()

    def get_absolute_url(self):
        slug = self.get_slug()
        if self.pub_date:
            return reverse('news_detail', kwargs={
                'year': self.pub_date.year, 'month': self.pub_date.month,
                'day': self.pub_date.day, 'slug': slug})
        return reverse('news_detail', kwargs={'slug': slug})

    def get_preview_url(self):
        slug = self.get_slug()
        return reverse('news_preview', kwargs={'slug': slug})

    def get_slug(self):
        lang = get_language()
        return get_preferred_translation_from_lang(self, lang).slug

    def get_title(self):
        lang = get_language()
        return get_preferred_translation_from_lang(self, lang).title

    def is_published(self):
        lang = get_language()
        return (get_preferred_translation_from_lang(self, lang).is_published
                and (not self.pub_date or self.pub_date <= now()))


class NewsEntryTitle(models.Model):
    """
    The translateable fields of the ``NewsEntry`` model.

    :title: The title of the entry.
    :slug: Slug to be used in the url only.
    :is_published: If ``True`` the object will be visible on it's pub_date.

    """
    title = models.CharField(
        max_length=512,
        verbose_name=_('Title'),
    )

    slug = models.SlugField(
        max_length=512,
        verbose_name=_('Slug'),
    )

    is_published = models.BooleanField(
        verbose_name=_('Is published'),
        default=False,
    )

    # Needed by simple-translation
    entry = models.ForeignKey(
        NewsEntry, verbose_name=_('News entry'))

    language = models.CharField(
        max_length=5, verbose_name=('Language'), choices=settings.LANGUAGES)


class RecentPlugin(CMSPlugin):
    """Plugin model to display recent news."""
    limit = models.PositiveIntegerField(
        verbose_name=_('Maximum news amount'),
    )
    current_language_only = models.BooleanField(
        verbose_name=_('Only show entries for the selected language'),
    )
