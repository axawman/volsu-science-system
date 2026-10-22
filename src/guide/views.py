from django.db.models import Prefetch, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render

from .models import GuideFile, GuideSection


def _visible_sections(user):
    sections = GuideSection.objects.all()
    if not user.is_staff:
        sections = sections.filter(is_published=True)
    return sections


def guide_index(request):
    sections = _visible_sections(request.user).prefetch_related(
        Prefetch("files", queryset=GuideFile.objects.filter(is_published=True))
    )
    general_files = GuideFile.objects.filter(is_published=True, section__isnull=True)

    return render(request, "guide/index.html", {
        "sections": sections,
        "general_files": general_files,
    })


def guide_section(request, slug):
    sections = list(_visible_sections(request.user))
    section = get_object_or_404(_visible_sections(request.user), slug=slug)
    position = next(index for index, item in enumerate(sections) if item.id == section.id)

    return render(request, "guide/section_detail.html", {
        "section": section,
        "sections": sections,
        "files": section.files.filter(is_published=True),
        "previous_section": sections[position - 1] if position > 0 else None,
        "next_section": sections[position + 1] if position + 1 < len(sections) else None,
    })


def guide_file_download(request, file_id):
    files = GuideFile.objects.all()
    if not request.user.is_staff:
        files = files.filter(
            Q(section__isnull=True) | Q(section__is_published=True),
            is_published=True,
        )
    guide_file = get_object_or_404(files, id=file_id)

    return FileResponse(
        guide_file.file.open("rb"),
        as_attachment=True,
        filename=guide_file.filename,
    )
