from django.contrib import admin

from .models import Evidence, Protein, Site


@admin.register(Protein)
class ProteinAdmin(admin.ModelAdmin):
    list_display = ("gene", "accession", "name", "organism")
    search_fields = ("gene", "accession", "name")
    list_filter = ("organism",)


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 0


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("protein", "position", "evidence_count")
    search_fields = ("protein__gene", "protein__accession")
    list_select_related = ("protein",)
    inlines = [EvidenceInline]

    @admin.display(description="证据数量")
    def evidence_count(self, obj):
        return obj.evidence.count()


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("site", "kind", "method", "tissue", "pmid", "is_demo")
    list_filter = ("kind", "is_demo", "method")
    search_fields = ("site__protein__gene", "site__protein__accession", "pmid")


admin.site.site_header = "PalmAtlas 数据管理"
