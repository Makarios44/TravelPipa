from urllib.parse import quote

from django.contrib import admin
from django.utils.html import format_html

from .models import BookingRequest

STATUS_COLORS = {
    "pending": "#F47745",
    "contacted": "#FFB547",
    "confirmed": "#007F86",
    "rejected": "#8a8a8a",
    "cancelled": "#8a8a8a",
}


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ["reference", "created_at", "status_badge", "experience_name", "preferred_date", "people",
                    "full_name", "service_language"]
    list_display_links = ["reference", "full_name"]
    list_filter = ["status", "preferred_date", "experience", "service_language", "created_at"]
    search_fields = ["reference", "full_name", "email", "phone", "experience_title"]
    date_hierarchy = "created_at"
    list_per_page = 50
    actions = ["mark_contacted", "mark_confirmed", "mark_rejected", "mark_cancelled"]
    readonly_fields = ["reference", "uuid", "created_at", "updated_at", "experience_title", "preferred_date",
                       "people", "full_name", "email", "phone", "service_language", "site_language", "notes",
                       "consent_at", "notification_sent", "contact_links"]
    fieldsets = [
        ("Solicitação", {"fields": ["reference", "created_at", "experience", "experience_title",
                                    "preferred_date", "people"]}),
        ("Cliente", {"fields": ["full_name", "email", "phone", "contact_links", "service_language",
                                "site_language", "notes"]}),
        ("Atendimento", {"fields": ["status", "internal_notes"],
                         "description": "Atualize o status conforme o atendimento avança. "
                                        "O cliente não é avisado automaticamente."}),
        ("Registro", {"fields": ["uuid", "updated_at", "consent_at", "notification_sent"],
                      "classes": ["collapse"]}),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("experience")

    def has_add_permission(self, request):
        # Requests come only from the website form.
        return False

    @admin.display(description="experiência", ordering="experience_title")
    def experience_name(self, obj):
        return str(obj.experience) if obj.experience else obj.experience_title

    @admin.display(description="status", ordering="status")
    def status_badge(self, obj):
        color = STATUS_COLORS.get(obj.status, "#888")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;'
            'white-space:nowrap">{}</span>', color, obj.get_status_display())

    @admin.display(description="contato rápido")
    def contact_links(self, obj):
        if not obj.pk:
            return "—"
        greeting = {"pt-br": "Olá", "es": "Hola"}.get(obj.service_language, "Hello")
        text = quote(f"{greeting} {obj.full_name.split()[0]}! TravelPipa — {obj.reference}")
        parts = []
        if obj.phone_digits:
            parts.append(format_html('<a href="https://wa.me/{}?text={}" target="_blank" rel="noopener">'
                                     'Abrir WhatsApp</a>', obj.phone_digits, text))
        parts.append(format_html('<a href="mailto:{}?subject={}">Enviar e-mail</a>', obj.email,
                                 quote(f"TravelPipa — {obj.reference}")))
        return format_html(" &nbsp;|&nbsp; ".join(["{}"] * len(parts)), *parts)

    def _set_status(self, request, queryset, status, label):
        updated = queryset.update(status=status)
        self.message_user(request, f"{updated} solicitação(ões) marcada(s) como {label}.")

    @admin.action(description="Marcar como Contatado")
    def mark_contacted(self, request, queryset):
        self._set_status(request, queryset, BookingRequest.Status.CONTACTED, "Contatado")

    @admin.action(description="Marcar como Confirmada")
    def mark_confirmed(self, request, queryset):
        self._set_status(request, queryset, BookingRequest.Status.CONFIRMED, "Confirmada")

    @admin.action(description="Marcar como Recusada")
    def mark_rejected(self, request, queryset):
        self._set_status(request, queryset, BookingRequest.Status.REJECTED, "Recusada")

    @admin.action(description="Marcar como Cancelada")
    def mark_cancelled(self, request, queryset):
        self._set_status(request, queryset, BookingRequest.Status.CANCELLED, "Cancelada")
