from django.contrib import admin
from django.utils.html import format_html

from core.admin import image_preview, language_fieldsets

from .models import Category, Experience, ExperienceImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["__str__", "name_en", "slug", "is_transfer", "order", "active", "experience_count"]
    list_editable = ["order", "active"]
    list_filter = ["active", "is_transfer"]
    search_fields = ["name_en", "name_pt", "name_es"]
    prepopulated_fields = {"slug": ["name_en"]}
    readonly_fields = ["preview"]
    fieldsets = [
        ("Geral", {"fields": ["slug", "image", "preview", "icon", "is_transfer", "order", "active"]}),
        *language_fieldsets("name", "description"),
    ]

    @admin.display(description="experiências")
    def experience_count(self, obj):
        return obj.experiences.count()

    @admin.display(description="prévia")
    def preview(self, obj):
        return image_preview(obj.image, 90)


class ExperienceImageInline(admin.StackedInline):
    model = ExperienceImage
    extra = 1
    fields = [("image", "preview"), ("is_cover", "order"), ("alt_en", "alt_pt", "alt_es")]
    readonly_fields = ["preview"]
    verbose_name = "foto"
    verbose_name_plural = "galeria de fotos (a primeira marcada como capa aparece nos cartões)"

    @admin.display(description="prévia")
    def preview(self, obj):
        return image_preview(obj.image if obj and obj.pk else None, 80)


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ["thumb", "__str__", "category", "price_display", "featured", "active", "order",
                    "is_demo", "updated_at"]
    list_display_links = ["thumb", "__str__"]
    list_editable = ["featured", "active", "order"]
    list_filter = ["active", "featured", "category", "is_demo"]
    search_fields = ["title_en", "title_pt", "title_es", "slug"]
    prepopulated_fields = {"slug": ["title_en"]}
    autocomplete_fields = ["category"]
    inlines = [ExperienceImageInline]
    save_on_top = True
    actions = ["activate", "deactivate", "duplicate"]
    fieldsets = [
        ("Geral", {
            "fields": ["category", "slug", ("active", "featured", "order"), ("tide_dependent", "cadastur_guide"), "is_demo"],
        }),
        ("Preço", {
            "fields": [("price", "currency"), ("price_unit", "price_is_starting")],
            "description": "Deixe o preço vazio para exibir “preço sob consulta”.",
        }),
        ("Detalhes do transfer (somente para a categoria Transfers)", {
            "fields": [("origin_en", "destination_en"), ("origin_pt", "destination_pt"),
                       ("origin_es", "destination_es"), ("transfer_type", "max_passengers")],
            "classes": ["collapse"],
        }),
        ("Vídeo (opcional)", {
            "fields": ["video", "video_poster"],
            "description": "Aparece na página da experiência, abaixo da descrição.",
        }),
        *language_fieldsets("title", "summary", "description", "duration", "itinerary", "included",
                            "not_included", "important_info", "cancellation_policy"),
        *[(f"SEO — {name}", {"fields": [f"meta_title_{s}", f"meta_description_{s}"], "classes": ["collapse"],
                             "description": "Opcional. Vazio = usa o título e o resumo."})
          for s, name in (("en", "Inglês"), ("pt", "Português"), ("es", "Espanhol"))],
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("category").prefetch_related("images")

    @admin.display(description="foto")
    def thumb(self, obj):
        cover = obj.cover
        return image_preview(cover.image if cover else None, 44)

    @admin.display(description="preço")
    def price_display(self, obj):
        if obj.price is None:
            return format_html('<span style="color:#888">sob consulta</span>')
        return f"{obj.currency} {obj.price:,.2f}"

    @admin.action(description="Ativar selecionadas")
    def activate(self, request, queryset):
        queryset.update(active=True)

    @admin.action(description="Desativar selecionadas")
    def deactivate(self, request, queryset):
        queryset.update(active=False)

    @admin.action(description="Duplicar selecionadas (cópia desativada)")
    def duplicate(self, request, queryset):
        for obj in queryset:
            images = list(obj.images.all())
            obj.pk = None
            obj.id = None
            obj._state.adding = True
            obj.slug = ""
            obj.title_en = f"{obj.title_en} (copy)"
            obj.active = False
            obj.featured = False
            obj.save()
            for img in images:
                img.pk = None
                img.id = None
                img._state.adding = True
                img.experience = obj
                img.save()
        self.message_user(request, "Cópias criadas como inativas. Revise antes de ativar.")
