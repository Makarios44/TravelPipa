"""
Runs on every start (bin/start.sh), right after the migrations. Safe to repeat:
it never overwrites what the team changed in the panel.

* First start on an empty database: loads the real tours, photos and videos
  (``load_tours``).
* Fills the contact e-mail with suporte@travelpipa.com.br when it is empty.
* Creates the first panel user from DJANGO_SUPERUSER_USERNAME /
  DJANGO_SUPERUSER_PASSWORD / DJANGO_SUPERUSER_EMAIL when no admin user exists yet.
* Prints a launch checklist in the deploy log.
"""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import SiteSettings
from tours.models import Experience

DEFAULT_CONTACT_EMAIL = "suporte@travelpipa.com.br"


class Command(BaseCommand):
    help = "Prepara o site no primeiro deploy e mostra o que ainda falta configurar."

    def handle(self, *args, **options):
        if not Experience.objects.exists():
            self.stdout.write("Banco vazio: carregando os passeios reais (load_tours)...")
            call_command("load_tours", stdout=self.stdout)

        site = SiteSettings.load()
        changed = []
        if not site.email:
            site.email = DEFAULT_CONTACT_EMAIL
            changed.append("email")
        if not site.site_name:
            site.site_name = "TravelPipa"
            changed.append("site_name")
        if changed:
            site.save()
            self.stdout.write(f"Configurações preenchidas: {', '.join(changed)}")

        self.create_first_user()
        self.checklist(SiteSettings.load())

    def create_first_user(self):
        User = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if not (username and password):
            return
        user = User.objects.filter(username__iexact=username).first()
        if user:
            # Password recovery: putting the variable back and redeploying sets a new password.
            user.set_password(password)
            user.is_active = user.is_staff = user.is_superuser = True
            user.save()
            cache.clear()  # also lifts any login lock from failed attempts
            self.stdout.write(self.style.SUCCESS(
                f"Senha do usuário '{user.username}' redefinida. Agora apague DJANGO_SUPERUSER_PASSWORD "
                "das variáveis do Railway."))
            return
        if User.objects.filter(is_superuser=True).exists():
            return
        User.objects.create_superuser(username=username, password=password,
                                      email=os.environ.get("DJANGO_SUPERUSER_EMAIL", DEFAULT_CONTACT_EMAIL))
        self.stdout.write(self.style.SUCCESS(
            f"Usuário '{username}' criado. Agora apague DJANGO_SUPERUSER_PASSWORD das variáveis do Railway."))

    def checklist(self, site):
        warnings = []
        if settings.DEBUG:
            warnings.append("DEBUG está ligado: use DEBUG=False em produção.")
        if not settings.SITE_URL.startswith("https://"):
            warnings.append("SITE_URL não definido (ex.: https://travelpipa.com.br).")
        if not os.environ.get("MEDIA_ROOT"):
            warnings.append("MEDIA_ROOT vazio: monte um Volume em /data e use MEDIA_ROOT=/data/media, "
                            "senão as fotos somem a cada deploy.")
        if not settings.EMAIL_ENABLED:
            warnings.append("E-mail desligado: defina RESEND_API_KEY para receber avisos de reservas.")
        if not get_user_model().objects.filter(is_staff=True, is_active=True).exists():
            warnings.append("Nenhum usuário do painel: defina DJANGO_SUPERUSER_USERNAME e "
                            "DJANGO_SUPERUSER_PASSWORD e faça um novo deploy.")
        digits = site.whatsapp_digits
        if not digits or set(digits[2:]) <= {"0"}:
            warnings.append("WhatsApp não preenchido (painel > Configurações).")
        if not site.company_document:
            warnings.append("CNPJ não preenchido (painel > Configurações) — aparece no rodapé.")
        if site.trust_cadastur_guides and not site.cadastur:
            warnings.append("Número do Cadastur não preenchido (painel > Configurações).")
        no_photo = [e.title_pt or e.title_en for e in Experience.objects.filter(active=True, images__isnull=True)]
        if no_photo:
            warnings.append("Passeio(s) ativo(s) sem foto: " + "; ".join(no_photo) + ".")
        demo = Experience.objects.filter(is_demo=True, active=True).count()
        if demo:
            warnings.append(f"{demo} passeio(s) de demonstração ativos: desative no painel.")

        if warnings:
            self.stdout.write(self.style.WARNING("Checklist de publicação — pendências:"))
            for item in warnings:
                self.stdout.write(self.style.WARNING(f"  • {item}"))
        else:
            self.stdout.write(self.style.SUCCESS("Checklist de publicação: tudo certo."))
