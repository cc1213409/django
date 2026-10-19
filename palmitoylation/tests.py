import csv
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .management.commands.import_records import COLUMNS
from .models import Evidence, Protein, Site


class DatabaseWorkflowTests(TestCase):
    def setUp(self):
        self.protein = Protein.objects.create(
            accession="TEST1", gene="GENE1", name="Protein One", organism="Human", sequence="AACAA"
        )
        self.site = Site.objects.create(protein=self.protein, position=3)
        Evidence.objects.create(site=self.site, kind="experimental", method="ABE", pmid="12345")
        mouse = Protein.objects.create(accession="DEMO1", gene="DEMOG", name="Demo", organism="Mouse")
        demo_site = Site.objects.create(protein=mouse, position=2)
        Evidence.objects.create(site=demo_site, kind="predicted", is_demo=True)

    def test_search_filters_detail_and_analysis(self):
        result = self.client.get(reverse("browse"), {"q": "GENE1"})
        self.assertEqual(result.context["total"], 1)
        self.assertContains(result, "GENE1")
        self.assertEqual(self.client.get(reverse("browse"), {"scope": "real"}).context["total"], 1)
        self.assertEqual(self.client.get(reverse("browse"), {"organism": "Mouse", "kind": "experimental"}).context["total"], 0)
        detail = self.client.get(reverse("detail", args=[self.site.pk]))
        self.assertContains(detail, "AA[C]AA")
        self.assertContains(detail, "PMID 12345")
        analysis = self.client.get(reverse("analysis"), {"scope": "real"})
        self.assertEqual(analysis.context["site_count"], 1)
        self.assertEqual(analysis.context["evidence_count"], 1)
        self.assertEqual(self.client.get(reverse("detail", args=[99999])).status_code, 404)

    def test_evidence_filters_apply_to_same_row(self):
        Evidence.objects.create(site=self.site, kind="predicted", method="demo", is_demo=True)
        result = self.client.get(reverse("browse"), {"scope": "real", "kind": "predicted"})
        self.assertEqual(result.context["total"], 0)

    def test_export_uses_matching_evidence_and_escapes_formulas(self):
        item = Evidence.objects.get(site=self.site, kind="experimental")
        item.notes = "=1+1"
        item.save()
        result = self.client.get(reverse("export_csv"), {"scope": "real"})
        rows = list(csv.DictReader(result.content.decode("utf-8-sig").splitlines()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["notes"], "'=1+1")
        self.assertEqual(rows[0]["accession"], "TEST1")

    def test_site_sequence_validation(self):
        self.site.position = 2
        with self.assertRaises(ValidationError):
            self.site.full_clean()

    def test_csv_import_rolls_back_invalid_rows_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "records.csv"

            def write(positions):
                with file.open("w", encoding="utf-8", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=COLUMNS)
                    writer.writeheader()
                    for position in positions:
                        writer.writerow({"accession": "NEW1", "gene": "NEW", "name": "New protein",
                                         "organism": "Human", "sequence": "AACAA", "position": position,
                                         "kind": "experimental"})

            write([3, 2])
            with self.assertRaises(CommandError):
                call_command("import_records", str(file))
            self.assertFalse(Protein.objects.filter(accession="NEW1").exists())
            write([3])
            call_command("import_records", str(file))
            call_command("import_records", str(file))
            self.assertEqual(Protein.objects.filter(accession="NEW1").count(), 1)
            self.assertEqual(Evidence.objects.filter(site__protein__accession="NEW1").count(), 1)

    def test_admin_requires_login(self):
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)
