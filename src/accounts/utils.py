import re


VOLSU_EMAIL_DOMAIN = "volsu.ru"
STUDY_PROGRAM_LABELS = {
    "pmi": "ПМИ",
}
STUDY_LEVEL_LABELS = {
    "b": "б",
    "m": "м",
    "s": "с",
}


def parse_volsu_student_email(email):
    if not email:
        return None

    try:
        local_part, domain = email.strip().lower().split("@", 1)
        group_code, record_book_number = local_part.rsplit("_", 1)
    except ValueError:
        return None

    if domain != VOLSU_EMAIL_DOMAIN or not record_book_number.isdigit():
        return None

    match = re.fullmatch(r"([a-z]+)-(\d+)", group_code)
    if not match:
        return None

    letter_code = match.group(1)
    group_number = match.group(2)
    if len(letter_code) < 2:
        return None

    program_code = letter_code[:-1]
    level_code = letter_code[-1]
    program_label = STUDY_PROGRAM_LABELS.get(program_code, program_code.upper())
    level_label = STUDY_LEVEL_LABELS.get(level_code, level_code)

    return {
        "group_code": group_code,
        "group_name": f"{program_label}{level_label}-{group_number}",
        "record_book_number": record_book_number,
    }


def get_student_record_book_number(email):
    student_data = parse_volsu_student_email(email)
    if not student_data:
        return "-"

    return student_data["record_book_number"]
