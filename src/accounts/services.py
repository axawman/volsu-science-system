from .models import StudyGroup
from .utils import parse_volsu_student_email


def assign_study_group_from_email(profile):
    student_data = parse_volsu_student_email(profile.user.email)
    if not student_data:
        return None

    study_group, _ = StudyGroup.objects.get_or_create(
        code=student_data["group_code"],
        defaults={"display_name": student_data["group_name"]},
    )

    if profile.study_group_id != study_group.id:
        profile.study_group = study_group
        profile.save(update_fields=["study_group"])

    return study_group
