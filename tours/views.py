from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from core.context_processors import whatsapp_link
from core.models import SiteSettings, Testimonial
from core.seo import breadcrumb_schema, experience_schema, json_ld

from .models import Category, Experience


def experience_list(request):
    categories = list(Category.objects.active())
    experiences = Experience.objects.published()
    selected = None
    slug = request.GET.get("category", "").strip()
    if slug:
        selected = next((c for c in categories if c.slug == slug), None)
        if selected:
            experiences = experiences.filter(category=selected)
    return render(request, "tours/experience_list.html", {
        "categories": categories,
        "selected_category": selected,
        "experiences": experiences,
        "filtered": bool(slug),
    })


def experience_detail(request, slug):
    experience = get_object_or_404(Experience.objects.published(), slug=slug)
    site = SiteSettings.load()
    message = _("Hello! I'm interested in \"%(title)s\" (%(url)s).") % {
        "title": experience.title,
        "url": request.build_absolute_uri(experience.get_absolute_url()),
    }
    related = (Experience.objects.published().filter(category=experience.category)
               .exclude(pk=experience.pk)[:3])
    testimonials = Testimonial.objects.published().filter(experience=experience).order_by("-review_date", "-created_at")[:3]
    list_url = reverse("tours:transfers") if experience.is_transfer else reverse("tours:experience_list")
    list_name = _("Transfers") if experience.is_transfer else _("Experiences")
    breadcrumbs = [(_("Home"), reverse("core:home")), (list_name, list_url),
                   (experience.title, experience.get_absolute_url())]
    schemas = [breadcrumb_schema(request, breadcrumbs)]
    if not experience.is_demo:
        schemas.insert(0, experience_schema(request, experience, site))
    return render(request, "tours/experience_detail.html", {
        "experience": experience,
        "related": related,
        "testimonials": testimonials,
        "breadcrumbs": breadcrumbs,
        "whatsapp_url": whatsapp_link(site, message),
        "cancellation_policy": experience.cancellation_policy or site.default_cancellation,
        "schema": mark_safe("".join(json_ld(s) for s in schemas)),
    })


def transfers(request):
    items = list(Experience.objects.transfers().order_by("-featured", "order"))
    return render(request, "tours/transfers.html", {
        "transfers": items,
        "main_transfer": items[0] if items else None,
        "other_transfers": items[1:],
    })
