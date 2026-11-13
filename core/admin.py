from django.contrib import admin
from django.utils.html import format_html

from .i18n import SUFFIXES, SUFFIX_LABELS
from .models import ContactMessage, SiteSettings, Testimonial


def language_fieldsets(*bases, title="Conteúdo", required_note=True, collapse=False):
    """One fieldset per language, e.g. ("Conteúdo — Inglês", {"fields": [title_en, ...]})."""
    sets = []
    for suffix in SUFFIXES:
        label = f"{title} — {SUFFIX_LABELS[suffix]}"
        if suffix == "en" and required_note:
            label += " (idioma padrão do site)"
        options = {"fields": [f"{base}_{suffix}" for base in bases]}
        if collapse:
            options["classes"] = ["collapse"]
        sets.append((label, options))
    return sets


def image_preview(field_file, height=60):
    if not field_file:
        return "—"
    return format_html('<img src="{}" style="height:{}px;border-radius:6px;object-fit:cover" alt="">',
                       field_file.url, height)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    readonly_fields = ["logo_preview", "hero_preview", "updated_at"]
    fieldsets = [
        ("Identidade", {"fields": ["site_name", "logo", "logo_preview", "hero_image", "hero_preview",
                                   "about_image", "og_image"]}),
        ("Contato", {"fields": ["whatsapp", "phone", "email", "address", "google_maps_url"]}),
        ("Redes sociais", {"fields": ["instagram", "facebook", "tiktok", "youtube", "tripadvisor"]}),
        ("Dados da empresa (opcional, exibidos no rodapé)", {
            "fields": ["company_legal_name", "company_document", "cadastur"]}),
        ("Selos de confiança", {
            "fields": ["trust_cadastur_guides", "trust_der_vehicles"],
            "description": "Aparecem na faixa acima do rodapé e perto do botão de reserva. "
                           "Desmarque se algum cadastro deixar de valer."}),
        *language_fieldsets("opening_hours", "about_intro", "about_body", "pipa_region",
                            "default_cancellation", title="Textos institucionais"),
        *language_fieldsets("privacy_policy", "terms", title="Páginas legais", required_note=False, collapse=True),
        ("Registro", {"fields": ["updated_at"]}),
    ]

    @admin.display(description="prévia do logotipo")
    def logo_preview(self, obj):
        return image_preview(obj.logo)

    @admin.display(description="prévia do banner")
    def hero_preview(self, obj):
        return image_preview(obj.hero_image, 90)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Go straight to the single settings form.
        from django.shortcuts import redirect

        obj = SiteSettings.load()
        return redirect("admin:core_sitesettings_change", obj.pk)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["author_name", "author_country", "experience", "rating", "source", "confirmed_real",
                    "active", "order"]
    list_editable = ["active", "order"]
    list_filter = ["active", "confirmed_real", "source"]
    search_fields = ["author_name", "text_en", "text_pt", "text_es"]
    autocomplete_fields = ["experience"]
    fieldsets = [
        ("Cliente", {"fields": ["author_name", "author_country", "experience", "rating", "source", "review_date"]}),
        ("Texto", {"fields": ["text_en", "text_pt", "text_es"],
                   "description": "Cada idioma do site exibe apenas os depoimentos escritos naquele idioma."}),
        ("Publicação", {"fields": ["confirmed_real", "active", "order"]}),
    ]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "subject", "language", "created_at", "handled"]
    list_filter = ["handled", "language", "created_at"]
    list_editable = ["handled"]
    search_fields = ["name", "email", "subject", "message"]
    date_hierarchy = "created_at"
    readonly_fields = ["name", "email", "phone", "language", "subject", "message", "consent_at", "created_at"]
    fields = readonly_fields + ["handled", "internal_notes"]

    def has_add_permission(self, request):
        return False
