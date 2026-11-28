import shutil
import tempfile
from importlib import import_module
from io import BytesIO

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from tours.models import Category, Experience, ExperienceImage

TEMP_MEDIA = tempfile.mkdtemp()
migration = import_module("tours.migrations.0012_byd_cover_and_inside_album")


def image_file(name):
    buffer = BytesIO()
    Image.new("RGB", (40, 30), (10, 20, 30)).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class BydMigrationTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def test_byd_cover_inside_album_and_partner_wording(self):
        cat = Category.objects.create(name_en="Transfers", slug="transfers", is_transfer=True)
        exp = Experience.objects.create(
            category=cat, slug="natal-airport-pipa-transfer", title_en="Transfer",
            important_info_pt="Bagagem incluída\nVeículos cadastrados para transporte turístico no DER/RN",
            important_info_en="Edited by the team")
        names = ["01-carro-eletrico-mirante.jpg", "03-spin-7-lugares-frente.jpg", "04-byd-interior-painel.jpg",
                 "07-spin-lateral.jpg", "08-byd-traseira.jpg", "foto-nova.jpg"]
        for i, name in enumerate(names):
            ExperienceImage.objects.create(experience=exp, image=image_file(name), order=i, is_cover=(i == 0),
                                           alt_pt="Lateral do carro de 7 lugares, com selo de transporte "
                                                  "turístico do DER/RN" if name.startswith("07") else "")
        migration.forwards(apps, None)
        exp.refresh_from_db()
        self.assertTrue(exp.cover.image.name.split("/")[-1].startswith("08-byd-traseira"))
        self.assertEqual([i.image.name.split("/")[-1][:2] for i in exp.inside_gallery], ["04"])
        main = [i.image.name.split("/")[-1][:2] for i in sorted(exp.gallery, key=lambda i: i.order)]
        self.assertEqual(main, ["08", "03", "07", "01", "fo"])
        self.assertEqual(exp.important_info_pt.split("\n")[1],
                         "Transporte feito por parceiros cadastrados no DER/RN para transporte turístico")
        self.assertEqual(exp.important_info_en, "Edited by the team")
        spin = next(i for i in exp.images.all() if "07-spin" in i.image.name)
        self.assertNotIn("DER", spin.alt_pt)


class AccreditedDriversMigrationTests(TestCase):
    def test_replaces_only_untouched_lines(self):
        m = import_module("tours.migrations.0013_accredited_drivers_wording")
        cat = Category.objects.create(name_en="Transfers", slug="transfers", is_transfer=True)
        exp = Experience.objects.create(
            category=cat, slug="t", title_en="T",
            important_info_pt="Bagagem incluída\nTransporte feito por parceiros cadastrados no DER/RN para "
                              "transporte turístico\nCadeirinha sob consulta",
            important_info_en="Edited by the team")
        m.forwards(apps, None)
        exp.refresh_from_db()
        self.assertEqual(exp.important_info_pt.split("\n"), [
            "Bagagem incluída",
            "Transporte feito pela nossa rede de motoristas parceiros credenciados no DER/RN para transporte turístico",
            "Carro e motorista confirmados até 12 horas antes da viagem, com foto do carro e do motorista",
            "Cadeirinha sob consulta"])
        self.assertEqual(exp.important_info_en, "Edited by the team")
