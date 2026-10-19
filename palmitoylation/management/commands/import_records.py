import csv

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from palmitoylation.models import Evidence, Protein, Site


COLUMNS = ("accession", "gene", "name", "organism", "sequence", "position", "kind", "method", "tissue", "pmid", "notes")
REQUIRED = ("accession", "gene", "name", "organism", "position", "kind")


class Command(BaseCommand):
    help = "从 UTF-8 CSV 原子导入蛋白、位点和证据；重复导入更新对应记录。"

    def add_arguments(self, parser):
        parser.add_argument("file", help="CSV 文件路径")
        parser.add_argument("--demo", action="store_true", help="将导入证据标记为虚构演示数据")

    def handle(self, *args, **options):
        count = 0
        try:
            with open(options["file"], encoding="utf-8-sig", newline="") as source, transaction.atomic():
                reader = csv.DictReader(source)
                missing = set(COLUMNS) - set(reader.fieldnames or [])
                if missing:
                    raise CommandError("CSV 缺少列：" + ", ".join(sorted(missing)))
                for line, row in enumerate(reader, start=2):
                    try:
                        values = {column: (row.get(column) or "").strip() for column in COLUMNS}
                        if any(not values[column] for column in REQUIRED):
                            raise ValueError("必填列不能为空")
                        position = int(values["position"])
                        sequence = values["sequence"].upper()
                        protein, _ = Protein.objects.get_or_create(
                            accession=values["accession"], organism=values["organism"],
                            defaults={"gene": values["gene"], "name": values["name"], "sequence": sequence},
                        )
                        protein.gene, protein.name = values["gene"], values["name"]
                        if sequence:
                            protein.sequence = sequence
                        protein.full_clean()
                        protein.save()
                        for prior_site in protein.sites.all():
                            prior_site.full_clean()
                        site, _ = Site.objects.get_or_create(protein=protein, position=position)
                        site.full_clean()
                        identity = {
                            "site": site, "kind": values["kind"], "method": values["method"],
                            "tissue": values["tissue"], "pmid": values["pmid"],
                        }
                        evidence, _ = Evidence.objects.get_or_create(**identity, defaults={
                            "notes": values["notes"], "is_demo": options["demo"],
                        })
                        if evidence.is_demo != options["demo"]:
                            raise ValueError("该证据已存在，但演示标记不同；请检查 CSV")
                        evidence.notes = values["notes"]
                        evidence.full_clean()
                        evidence.save()
                        count += 1
                    except (ValueError, ValidationError) as error:
                        raise CommandError(f"CSV 第 {line} 行无效：{error}") from error
        except OSError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"成功导入或更新 {count} 条证据记录"))
