"""
TravelPipa management panel ("Gestão"): a simple, mobile-friendly area for the
team to manage tours, photos, bookings and site information, without the
technical Django admin.

Access: logged-in staff users only (is_staff). Every change is a POST with CSRF.
"""
import hashlib
import json
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from bookings.models import BookingRequest
from core.antispam import client_ip_hash
from core.models import ContactMessage, SiteSettings, Testimonial
from tours.models import Category, Experience, ExperienceImage

from .forms import (BookingUpdateForm, CategoryForm, ExperienceForm, PanelLoginForm, PanelPasswordChangeForm,
                    PhotoAltForm, PhotoUploadForm, SiteSettingsForm, TestimonialForm)

ACTIVE_STATUSES = [BookingRequest.Status.PENDING, BookingRequest.Status.CONTACTED, BookingRequest.Status.CONFIRMED]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def staff_required(view):
    @wraps(view)
    @never_cache
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('panel:login')}?next={quote(request.get_full_path())}")
        if not request.user.is_staff:
            logout(request)
            messages.error(request, "Este usuário não tem acesso ao painel.")
            return redirect("panel:login")
        response = view(request, *args, **kwargs)
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response
    return wrapper


def panel_render(request, template, context=None, status=200):
    context = context or {}
    context.setdefault("site", SiteSettings.load())
    context["nav_counts"] = {
        "bookings": BookingRequest.objects.filter(status=BookingRequest.Status.PENDING).count(),
        "messages": ContactMessage.objects.filter(handled=False).count(),
    }
    context["section"] = context.get("section", "")
    return render(request, template, context, status=status)


def wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch"


def back(request, default):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        return redirect(target)
    return redirect(default)


# --------------------------------------------------------------------------
# Login / logout / password
# --------------------------------------------------------------------------
def _lock_key(request, username):
    return f"panel-login:{client_ip_hash(request)}:{(username or '').strip().lower()}"


def _user_lock_key(username):
    """Attempts on one username from any IP (stops attacks spread over many addresses)."""
    digest = hashlib.sha256((username or "").strip().lower().encode()).hexdigest()[:32]
    return f"panel-login-user:{digest}"


def _user_limit():
    return settings.PANEL_LOGIN_MAX_ATTEMPTS * 4


@never_cache
def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("panel:dashboard")
    form = PanelLoginForm(request, data=request.POST or None)
    locked = False
    if request.method == "POST":
        username = request.POST.get("username")
        key = _lock_key(request, username)
        user_key = _user_lock_key(username)
        attempts = cache.get(key, 0)
        if attempts >= settings.PANEL_LOGIN_MAX_ATTEMPTS or cache.get(user_key, 0) >= _user_limit():
            locked = True
            form = PanelLoginForm(request)  # do not even check the password
        elif form.is_valid():
            cache.delete(key)
            cache.delete(user_key)
            login(request, form.get_user())
            nxt = request.POST.get("next") or request.GET.get("next")
            if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}, require_https=request.is_secure()):
                return redirect(nxt)
            return redirect("panel:dashboard")
        else:
            cache.set(key, attempts + 1, settings.PANEL_LOGIN_LOCK_MINUTES * 60)
            cache.set(user_key, cache.get(user_key, 0) + 1, settings.PANEL_LOGIN_LOCK_MINUTES * 60)
            if attempts + 1 >= settings.PANEL_LOGIN_MAX_ATTEMPTS:
                locked = True
    response = render(request, "panel/login.html", {
        "form": form, "locked": locked, "lock_minutes": settings.PANEL_LOGIN_LOCK_MINUTES,
        "next": request.GET.get("next", ""), "site": SiteSettings.load()})
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Você saiu do painel.")
    return redirect("panel:login")


@staff_required
def password_change(request):
    form = PanelPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Senha alterada.")
        return redirect("panel:dashboard")
    return panel_render(request, "panel/password.html", {"form": form, "section": "account"})


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@staff_required
def dashboard(request):
    today = timezone.localdate()
    upcoming = (BookingRequest.objects.filter(preferred_date__gte=today, status__in=ACTIVE_STATUSES)
                .select_related("experience").order_by("preferred_date", "created_at")[:6])
    latest = BookingRequest.objects.select_related("experience").order_by("-created_at")[:5]
    return panel_render(request, "panel/dashboard.html", {
        "section": "dashboard",
        "stats": {
            "pending": BookingRequest.objects.filter(status=BookingRequest.Status.PENDING).count(),
            "upcoming": BookingRequest.objects.filter(preferred_date__gte=today, status__in=ACTIVE_STATUSES).count(),
            "active_tours": Experience.objects.filter(active=True).count(),
            "inactive_tours": Experience.objects.filter(active=False).count(),
            "messages": ContactMessage.objects.filter(handled=False).count(),
        },
        "upcoming": upcoming,
        "latest": latest,
        "demo_count": Experience.objects.filter(is_demo=True, active=True).count(),
    })


# --------------------------------------------------------------------------
# Experiences
# --------------------------------------------------------------------------
@staff_required
def experience_list(request):
    qs = Experience.objects.select_related("category").prefetch_related("images").annotate(
        photo_count=Count("images"))
    q = request.GET.get("q", "").strip()
    show = request.GET.get("show", "all")
    category = request.GET.get("category", "")
    if q:
        qs = qs.filter(Q(title_pt__icontains=q) | Q(title_en__icontains=q) | Q(title_es__icontains=q))
    if show == "active":
        qs = qs.filter(active=True)
    elif show == "inactive":
        qs = qs.filter(active=False)
    if category:
        qs = qs.filter(category__slug=category)
    qs = qs.order_by("category__order", "order", "title_pt")
    return panel_render(request, "panel/experience_list.html", {
        "section": "experiences", "experiences": qs, "q": q, "show": show, "category": category,
        "categories": Category.objects.order_by("order"),
    })


TOGGLE_FIELDS = {"active", "featured"}


@staff_required
@require_POST
def experience_toggle(request, pk, field):
    if field not in TOGGLE_FIELDS:
        return HttpResponseBadRequest("Campo inválido")
    exp = get_object_or_404(Experience, pk=pk)
    value = request.POST.get("value")
    new_value = (value == "1") if value in ("0", "1") else not getattr(exp, field)
    setattr(exp, field, new_value)
    exp.save(update_fields=[field, "updated_at"])
    label = {"active": ("ativado", "desativado"), "featured": ("em destaque", "sem destaque")}[field]
    text = f"“{exp}” {label[0] if new_value else label[1]}."
    if wants_json(request):
        return JsonResponse({"ok": True, "value": new_value, "message": text})
    messages.success(request, text)
    return back(request, "panel:experiences")


@staff_required
def experience_edit(request, pk=None):
    exp = get_object_or_404(Experience, pk=pk) if pk else None
    form = ExperienceForm(request.POST or None, request.FILES or None, instance=exp)
    if request.method == "POST":
        if form.is_valid():
            exp = form.save()
            messages.success(request, "Passeio salvo." if pk else "Passeio criado. Agora adicione as fotos.")
            return redirect("panel:experience_edit", pk=exp.pk)
        messages.error(request, "Confira os campos destacados em vermelho.")
    photos = list(exp.images.all()) if exp else []
    return panel_render(request, "panel/experience_form.html", {
        "section": "experiences", "form": form, "experience": exp, "photos": photos,
        "photo_forms": [(p, PhotoAltForm(instance=p, prefix=f"p{p.pk}")) for p in photos],
        "upload_form": PhotoUploadForm(),
    })


@staff_required
def experience_delete(request, pk):
    exp = get_object_or_404(Experience, pk=pk)
    if request.method == "POST":
        name = str(exp)
        with transaction.atomic():
            for image in exp.images.all():
                image.image.delete(save=False)
            if exp.video:
                exp.video.delete(save=False)
            if exp.video_poster:
                exp.video_poster.delete(save=False)
            exp.delete()
        messages.success(request, f"“{name}” foi excluído. As reservas antigas continuam no histórico.")
        return redirect("panel:experiences")
    return panel_render(request, "panel/confirm_delete.html", {
        "section": "experiences", "object": exp, "kind": "passeio",
        "cancel_url": reverse("panel:experience_edit", args=[exp.pk]),
        "warning": "As fotos e o vídeo deste passeio também serão apagados. "
                   "Se quiser apenas tirar do site, use o botão “Ativo”.",
    })


# ---------- Photos ----------
@staff_required
@require_POST
def photo_upload(request, pk):
    exp = get_object_or_404(Experience, pk=pk)
    form = PhotoUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        for error in form.errors.get("photos", []):
            messages.error(request, error)
        return redirect(reverse("panel:experience_edit", args=[pk]) + "#fotos")
    next_order = (exp.images.aggregate(m=Max("order"))["m"] or 0) + 1 if exp.images.exists() else 0
    has_cover = exp.images.filter(is_cover=True).exists()
    with transaction.atomic():
        for i, upload in enumerate(form.cleaned_data["photos"]):
            ExperienceImage.objects.create(experience=exp, image=upload, order=next_order + i,
                                           is_cover=(not has_cover and i == 0))
    count = len(form.cleaned_data["photos"])
    messages.success(request, f"{count} foto(s) adicionada(s)." + ("" if has_cover else " A primeira virou a capa."))
    return redirect(reverse("panel:experience_edit", args=[pk]) + "#fotos")


@staff_required
@require_POST
def photo_action(request, pk, photo_pk, action):
    photo = get_object_or_404(ExperienceImage, pk=photo_pk, experience_id=pk)
    url = reverse("panel:experience_edit", args=[pk]) + "#fotos"
    if action == "cover":
        photo.is_cover = True
        photo.save()  # model clears the previous cover
        messages.success(request, "Capa alterada.")
    elif action == "delete":
        was_cover = photo.is_cover
        photo.image.delete(save=False)
        photo.delete()
        if was_cover:
            first = ExperienceImage.objects.filter(experience_id=pk).order_by("order", "id").first()
            if first:
                first.is_cover = True
                first.save()
        messages.success(request, "Foto excluída.")
    elif action in ("up", "down"):
        photos = list(ExperienceImage.objects.filter(experience_id=pk).order_by("order", "id"))
        index = photos.index(photo)
        swap = index - 1 if action == "up" else index + 1
        if 0 <= swap < len(photos):
            photos[index], photos[swap] = photos[swap], photos[index]
            for order, item in enumerate(photos):
                if item.order != order:
                    ExperienceImage.objects.filter(pk=item.pk).update(order=order)
    elif action == "alt":
        form = PhotoAltForm(request.POST, instance=photo, prefix=f"p{photo.pk}")
        if form.is_valid():
            form.save()
            messages.success(request, "Descrição da foto salva.")
        else:
            messages.error(request, "Não foi possível salvar a descrição.")
    else:
        return HttpResponseBadRequest("Ação inválida")
    return redirect(url)


@staff_required
@require_POST
def photo_reorder(request, pk):
    """Drag-and-drop order: JSON body {"order": [photo ids...]}."""
    exp = get_object_or_404(Experience, pk=pk)
    try:
        ids = [int(i) for i in json.loads(request.body or b"{}").get("order", [])]
    except (ValueError, TypeError, AttributeError):
        return HttpResponseBadRequest("Ordem inválida")
    valid = set(exp.images.values_list("pk", flat=True))
    if set(ids) != valid:
        return HttpResponseBadRequest("Ordem inválida")
    for order, photo_id in enumerate(ids):
        ExperienceImage.objects.filter(pk=photo_id).update(order=order)
    return JsonResponse({"ok": True, "message": "Ordem das fotos salva."})


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
@staff_required
def category_list(request):
    categories = Category.objects.annotate(total=Count("experiences")).order_by("order", "name_pt")
    return panel_render(request, "panel/category_list.html", {"section": "categories", "categories": categories})


@staff_required
def category_edit(request, pk=None):
    cat = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, request.FILES or None, instance=cat)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Categoria salva.")
            return redirect("panel:categories")
        messages.error(request, "Confira os campos destacados em vermelho.")
    return panel_render(request, "panel/simple_form.html", {
        "section": "categories", "form": form, "title": "Editar categoria" if cat else "Nova categoria",
        "back_url": reverse("panel:categories"), "multipart": True})


@staff_required
@require_POST
def category_toggle(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    cat.active = not cat.active
    cat.save(update_fields=["active", "updated_at"])
    text = f"Categoria “{cat}” {'ativada' if cat.active else 'desativada'}."
    if wants_json(request):
        return JsonResponse({"ok": True, "value": cat.active, "message": text})
    messages.success(request, text)
    return redirect("panel:categories")


# --------------------------------------------------------------------------
# Bookings
# --------------------------------------------------------------------------
@staff_required
def booking_list(request):
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    when = request.GET.get("when", "")
    qs = BookingRequest.objects.select_related("experience")
    if status in BookingRequest.Status.values:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(full_name__icontains=q) | Q(email__icontains=q)
                       | Q(phone__icontains=q) | Q(experience_title__icontains=q))
    if when == "upcoming":
        qs = qs.filter(preferred_date__gte=timezone.localdate()).order_by("preferred_date")
    else:
        qs = qs.order_by("-created_at")
    counts = dict(BookingRequest.objects.values_list("status").annotate(n=Count("id")))
    tabs = [("", "Todas", sum(counts.values()))] + [
        (value, label.split(" (")[0], counts.get(value, 0)) for value, label in BookingRequest.Status.choices]
    return panel_render(request, "panel/booking_list.html", {
        "section": "bookings", "bookings": qs[:200], "status": status, "q": q, "when": when, "tabs": tabs})


def whatsapp_for(booking):
    if not booking.phone_digits:
        return ""
    greeting = {"pt-br": "Olá", "es": "Hola"}.get(booking.service_language, "Hello")
    first_name = booking.full_name.split()[0] if booking.full_name else ""
    title = booking.experience.title_pt if booking.experience else booking.experience_title
    body = {
        "pt-br": f"{greeting}, {first_name}! Aqui é da TravelPipa, sobre a sua solicitação {booking.reference} ({title}).",
        "es": f"{greeting}, {first_name}! Te escribimos de TravelPipa sobre tu solicitud {booking.reference} ({title}).",
    }.get(booking.service_language,
          f"{greeting}, {first_name}! This is TravelPipa about your request {booking.reference} ({title}).")
    return f"https://wa.me/{booking.phone_digits}?text={quote(body)}"


@staff_required
def booking_detail(request, pk):
    booking = get_object_or_404(BookingRequest.objects.select_related("experience"), pk=pk)
    form = BookingUpdateForm(request.POST or None, instance=booking)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Solicitação {booking.reference} atualizada.")
        return redirect("panel:booking_detail", pk=pk)
    return panel_render(request, "panel/booking_detail.html", {
        "section": "bookings", "booking": booking, "form": form, "whatsapp_url": whatsapp_for(booking)})


# --------------------------------------------------------------------------
# Contact messages
# --------------------------------------------------------------------------
@staff_required
def message_list(request):
    show = request.GET.get("show", "open")
    qs = ContactMessage.objects.order_by("-created_at")
    if show == "open":
        qs = qs.filter(handled=False)
    return panel_render(request, "panel/message_list.html", {
        "section": "messages", "items": qs[:200], "show": show})


@staff_required
@require_POST
def message_toggle(request, pk):
    item = get_object_or_404(ContactMessage, pk=pk)
    item.handled = not item.handled
    item.save(update_fields=["handled", "updated_at"])
    messages.success(request, "Mensagem marcada como respondida." if item.handled else "Mensagem reaberta.")
    return back(request, "panel:messages")


# --------------------------------------------------------------------------
# Testimonials
# --------------------------------------------------------------------------
@staff_required
def testimonial_list(request):
    return panel_render(request, "panel/testimonial_list.html", {
        "section": "testimonials", "items": Testimonial.objects.select_related("experience").all()})


@staff_required
def testimonial_edit(request, pk=None):
    item = get_object_or_404(Testimonial, pk=pk) if pk else None
    form = TestimonialForm(request.POST or None, instance=item)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Depoimento salvo.")
            return redirect("panel:testimonials")
        messages.error(request, "Confira os campos destacados em vermelho.")
    return panel_render(request, "panel/simple_form.html", {
        "section": "testimonials", "form": form, "title": "Editar depoimento" if item else "Novo depoimento",
        "back_url": reverse("panel:testimonials"),
        "intro": "Cadastre apenas avaliações reais. O depoimento só aparece no site se estiver marcado como "
                 "real e publicado, e somente no idioma em que foi escrito."})


@staff_required
def testimonial_delete(request, pk):
    item = get_object_or_404(Testimonial, pk=pk)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Depoimento excluído.")
        return redirect("panel:testimonials")
    return panel_render(request, "panel/confirm_delete.html", {
        "section": "testimonials", "object": item, "kind": "depoimento",
        "cancel_url": reverse("panel:testimonials")})


# --------------------------------------------------------------------------
# Site settings
# --------------------------------------------------------------------------
@staff_required
def site_settings(request):
    site = SiteSettings.load()
    site = SiteSettings.objects.get(pk=site.pk)  # fresh copy, not the cached one
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=site)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Configurações salvas. O site já foi atualizado.")
            return redirect("panel:settings")
        messages.error(request, "Confira os campos destacados em vermelho.")
    return panel_render(request, "panel/settings.html", {"section": "settings", "form": form})
