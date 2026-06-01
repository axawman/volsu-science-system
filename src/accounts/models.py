from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class StudyGroup(models.Model):
    code = models.CharField("Код группы", max_length=32, unique=True)
    display_name = models.CharField("Название группы", max_length=64)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Учебная группа"
        verbose_name_plural = "Учебные группы"
        ordering = ("display_name",)

    def __str__(self):
        return self.display_name


class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="Пользователь")
    role = models.CharField("Роль", max_length=20, choices=ROLE_CHOICES, default="student")
    full_name = models.CharField("ФИО", max_length=255)
    bio = models.TextField("О себе", blank=True)
    photo = models.ImageField("Фотография", upload_to="profile_photos/", blank=True, null=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    last_seen_at = models.DateTimeField("Был онлайн", blank=True, null=True)
    study_group = models.ForeignKey(
        StudyGroup,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="members",
        verbose_name="Учебная группа",
    )
    is_primary_admin = models.BooleanField("Первичный администратор", default=False)
    admin_granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="granted_admin_profiles",
        verbose_name="Кто назначил администратором",
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def short_name(self):
        name = (self.full_name or self.user.get_full_name() or self.user.username).strip()
        parts = name.split()

        if len(parts) >= 3:
            return f"{parts[0]} {parts[1][0]}.{parts[2][0]}."
        if len(parts) == 2:
            return f"{parts[0]} {parts[1][0]}."
        return name

    @property
    def group_display_name(self):
        name = (self.full_name or self.user.get_full_name() or self.user.username).strip()
        parts = name.split()

        if len(parts) >= 2:
            return f"{parts[0]} {parts[1][0]}."
        return name

    @property
    def avatar_initial(self):
        name = (self.full_name or self.user.username).strip()
        return name[:1].upper() or "?"

    @property
    def role_name(self):
        if self.user.is_superuser or self.user.is_staff or self.role == "admin":
            return "Админ"
        return self.get_role_display()

    def is_admin(self):
        return self.user.is_superuser or self.user.is_staff or self.role == "admin"

    def is_student(self):
        return self.role == "student"

    def is_teacher(self):
        return self.role == "teacher"


class GroupChatMessage(models.Model):
    study_group = models.ForeignKey(
        StudyGroup,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Учебная группа",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="group_chat_messages",
        verbose_name="Автор",
    )
    text = models.TextField("Текст сообщения")
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="replies",
        verbose_name="Ответ на сообщение",
    )
    read_by = models.ManyToManyField(
        User,
        blank=True,
        related_name="read_group_chat_messages",
        verbose_name="Кем прочитано",
    )
    hidden_for = models.ManyToManyField(
        User,
        blank=True,
        related_name="hidden_group_chat_messages",
        verbose_name="Скрыто для пользователей",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    edited_at = models.DateTimeField("Дата редактирования", blank=True, null=True)
    is_deleted = models.BooleanField("Удалено", default=False)
    deleted_at = models.DateTimeField("Дата удаления", blank=True, null=True)

    class Meta:
        verbose_name = "Сообщение группового чата"
        verbose_name_plural = "Сообщения группового чата"
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=["study_group", "created_at", "id"]),
        ]

    def __str__(self):
        return f"{self.study_group}: {self.author}"

    def mark_edited(self):
        self.edited_at = timezone.now()
        self.save(update_fields=["edited_at"])

    def mark_deleted(self):
        self.text = ""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["text", "is_deleted", "deleted_at"])
