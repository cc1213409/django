import csv

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Evidence, Protein, Site


def matching_evidence(request):
    rows = Evidence.objects.all()
    if request.GET.get("scope") == "real":
        rows = rows.filter(is_demo=False)
    kind = request.GET.get("kind", "")
    if kind in Evidence.Kind.values:
        rows = rows.filter(kind=kind)
    return rows


def matching_sites(request):
    evidence = matching_evidence(request)
    sites = Site.objects.filter(pk__in=evidence.values("site_id"))
    organism = request.GET.get("organism", "").strip()
    if organism:
        sites = sites.filter(protein__organism=organism)
    query = request.GET.get("q", "").strip()
    if query:
        sites = sites.filter(
            Q(protein__gene__icontains=query)
            | Q(protein__accession__icontains=query)
            | Q(protein__name__icontains=query)
            | Q(pk__in=evidence.filter(notes__icontains=query).values("site_id"))
        )
    return sites.select_related("protein").order_by("protein__gene", "protein__accession", "position")


def filter_context(request):
    return {
        "filters": request.GET,
        "organisms": Protein.objects.order_by("organism").values_list("organism", flat=True).distinct(),
        "kinds": Evidence.Kind.choices,
    }


@require_GET
def browse(request):
    sites = matching_sites(request)
    params = request.GET.copy()
    params.pop("page", None)
    page = Paginator(sites.prefetch_related(Prefetch(
        "evidence", queryset=matching_evidence(request), to_attr="visible_evidence"
    )), 20).get_page(request.GET.get("page"))
    return render(request, "palmitoylation/browse.html", {
        **filter_context(request),
        "page": page,
        "total": page.paginator.count,
        "proteins": sites.values("protein_id").distinct().count(),
        "demo_count": matching_evidence(request).filter(site_id__in=sites.values("id"), is_demo=True).count(),
        "query_string": params.urlencode(),
    })


@require_GET
def detail(request, pk):
    site = get_object_or_404(Site.objects.select_related("protein").prefetch_related("evidence"), pk=pk)
    sequence = site.protein.sequence
    sequence_window = ""
    if sequence and site.position <= len(sequence):
        start = max(0, site.position - 8)
        sequence_window = f"{sequence[start:site.position - 1]}[{sequence[site.position - 1]}]{sequence[site.position:site.position + 7]}"
    return render(request, "palmitoylation/detail.html", {"site": site, "sequence_window": sequence_window})


def chart(queryset, field, label_map=None):
    rows = list(queryset.order_by().values(field).annotate(count=Count("pk")).order_by("-count", field)[:10])
    maximum = max((item["count"] for item in rows), default=1)
    for item in rows:
        item["label"] = (label_map or {}).get(item[field], item[field]) or "未填写"
        item["width"] = round(100 * item["count"] / maximum)
    return rows


@require_GET
def analysis(request):
    sites = matching_sites(request)
    evidence = matching_evidence(request).filter(site_id__in=sites.values("id"))
    return render(request, "palmitoylation/analysis.html", {
        **filter_context(request),
        "site_count": sites.count(),
        "evidence_count": evidence.count(),
        "demo_count": evidence.filter(is_demo=True).count(),
        "charts": [
            ("位点所属物种", chart(sites, "protein__organism")),
            ("基因位点数", chart(sites, "protein__gene")),
            ("证据类型", chart(evidence, "kind", dict(Evidence.Kind.choices))),
            ("研究方法", chart(evidence, "method")),
        ],
    })


@require_GET
def export_csv(request):
    sites = matching_sites(request)
    evidence = matching_evidence(request).filter(site_id__in=sites.values("id"))
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="palmatlas.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["accession", "gene", "name", "organism", "sequence", "position", "kind", "method", "tissue", "pmid", "notes", "is_demo"])
    for item in evidence.select_related("site__protein").order_by("site__protein__gene", "site__position", "id").iterator():
        protein = item.site.protein
        values = [protein.accession, protein.gene, protein.name, protein.organism, protein.sequence,
                  item.site.position, item.kind, item.method, item.tissue, item.pmid, item.notes, item.is_demo]
        # Prevent spreadsheet programs from interpreting text cells as formulas.
        writer.writerow(["'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value for value in values])
    return response
