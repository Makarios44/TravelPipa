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
import logging
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from core.media_repair import repair_missing_media
from core.models import SiteSettings
from tours.models import Experience

logger = logging.getLogger(__name__)

DEFAULT_CONTACT_EMAIL = "suporte@travelpipa.com.br"


def _on_volume(path):
    """True when ``path`` lives on a mounted disk (e.g. a Railway Volume at /data)."""
    current = os.path.abspath(path)
    while current not in ("/", ""):
        if os.path.ismount(current):
            return True
        current = os.path.dirname(current)
    return False


class Command(BaseCommand):
    help = "Prepara o site no primeiro deploy e mostra o que ainda falta configurar."

    def handle(self, *args, **options):
        # Each step is independent: one failing (e.g. a content problem) must not
        # stop the others (media repair, first user) nor the site from starting.
        failures = 0
        for step in (self.load_content, self.repair_media, self.fill_settings, self.create_first_user):
            try:
                step()
            except Exception:  # noqa: BLE001 - reported in the deploy log, site still starts
                failures += 1
                logger.exception("prepare_site: a etapa %s falhou", step.__name__)
                self.stdout.write(self.style.ERROR(f"ERRO na etapa {step.__name__} (detalhes acima)."))
        self.checklist(SiteSettings.load())
        if failures:
            raise CommandError(f"{failures} etapa(s) do prepare_site falharam; veja o log.")

    def load_content(self):
        if not Experience.objects.exists():
            self.stdout.write("Banco vazio: carregando os passeios reais (load_tours)...")
            call_command("load_tours", stdout=self.stdout)
        else:
            # New tours/transfers added to the code appear on the next deploy;
            # the ones already on the site (and edited in the panel) are left alone.
            call_command("load_tours", only_new=True, stdout=self.stdout)

    def repair_media(self):
        restored, missing = repair_missing_media()
        if restored:
            self.stdout.write(self.style.WARNING(
                f"{len(restored)} foto(s)/vídeo(s) estavam faltando e foram restaurados a partir de content/."))
        if missing:
            self.stdout.write(self.style.WARNING(
                f"{len(missing)} arquivo(s) de mídia sumiram e não têm cópia em content/ "
                "(fotos enviadas pelo painel): reenvie pelo painel. Ex.: " + ", ".join(missing[:5])))

    def fill_settings(self):
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
        elif not settings.DEBUG and not _on_volume(settings.MEDIA_ROOT):
            warnings.append(f"MEDIA_ROOT ({settings.MEDIA_ROOT}) não está num Volume: as fotos enviadas pelo "
                            "painel somem a cada deploy. No Railway: serviço do site > Attach Volume > /data.")
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
