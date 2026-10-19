from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Protein(models.Model):
    accession = models.CharField("蛋白编号", max_length=50)
    gene = models.CharField("基因符号", max_length=80, db_index=True)
    name = models.CharField("蛋白名称", max_length=240)
    organism = models.CharField("物种", max_length=120, db_index=True)
    sequence = models.TextField(
        "蛋白序列（可选）", blank=True,
        validators=[RegexValidator(r"^[ACDEFGHIKLMNPQRSTVWY]+$", "仅支持大写标准氨基酸字母")],
    )

    class Meta:
        ordering = ["gene", "accession"]
        constraints = [models.UniqueConstraint(fields=["accession", "organism"], name="unique_protein_per_organism")]

    def __str__(self):
        return f"{self.gene} · {self.accession} ({self.organism})"


class Site(models.Model):
    protein = models.ForeignKey(Protein, on_delete=models.CASCADE, related_name="sites")
    position = models.PositiveIntegerField("半胱氨酸位点（1 起）", validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["protein__gene", "position"]
        constraints = [models.UniqueConstraint(fields=["protein", "position"], name="unique_site_per_protein")]

    def clean(self):
        if self.protein_id and self.position and self.protein.sequence:
            if self.position > len(self.protein.sequence):
                raise ValidationError({"position": "位点超出蛋白序列长度"})
            if self.protein.sequence[self.position - 1] != "C":
                raise ValidationError({"position": "S-棕榈酰化位点必须为半胱氨酸 C"})

    def __str__(self):
        return f"{self.protein.gene} C{self.position}"


class Evidence(models.Model):
    class Kind(models.TextChoices):
        EXPERIMENTAL = "experimental", "实验验证"
        PREDICTED = "predicted", "计算预测"

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="evidence")
    kind = models.CharField("证据类型", max_length=20, choices=Kind.choices)
    method = models.CharField("研究方法", max_length=120, blank=True)
    tissue = models.CharField("组织 / 细胞", max_length=120, blank=True)
    pmid = models.CharField(
        "PubMed ID", max_length=16, blank=True,
        validators=[RegexValidator(r"^\d+$", "PMID 必须为数字")],
    )
    notes = models.TextField("备注", blank=True)
    is_demo = models.BooleanField("演示数据", default=False)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(
            fields=["site", "kind", "method", "tissue", "pmid"], name="unique_evidence_source"
        )]

    def __str__(self):
        return f"{self.site} · {self.get_kind_display()}"
