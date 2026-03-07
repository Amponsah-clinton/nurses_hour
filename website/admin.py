from django.contrib import admin

from .models import (
    Visit,
    UserProfile,
    MCQQuestion,
    CaseStudy,
    BookOrSlide,
    Payment,
    Inquiry,
    CaseStudyAccess,
    ResourceBookmark,
    PracticeSession,
    PracticeAnswer,
)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'program')
    list_filter = ('program',)
    search_fields = ('user__email', 'user__first_name', 'phone')
    raw_id_fields = ('user',)
    ordering = ('-user__date_joined',)


@admin.register(MCQQuestion)
class MCQQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text_short', 'correct_answer', 'program', 'paper', 'topic', 'created_at')
    list_filter = ('program', 'paper', 'correct_answer')
    search_fields = ('question_text', 'topic')
    list_editable = ('correct_answer', 'program', 'paper')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def question_text_short(self, obj):
        return (obj.question_text[:60] + '...') if len(obj.question_text) > 60 else obj.question_text

    question_text_short.short_description = 'Question'


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_at')
    search_fields = ('title', 'scenario', 'content')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(BookOrSlide)
class BookOrSlideAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'kind', 'created_at')
    list_filter = ('kind',)
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'amount', 'status', 'description_short', 'created_at')
    list_filter = ('status',)
    search_fields = ('user_email', 'description')
    list_editable = ('status',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def description_short(self, obj):
        return (obj.description[:40] + '...') if obj.description and len(obj.description) > 40 else (obj.description or '—')

    description_short.short_description = 'Description'


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'subject', 'replied_at', 'created_at')
    list_filter = ('replied_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(CaseStudyAccess)
class CaseStudyAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'case_study', 'payment', 'created_at')
    list_filter = ('case_study',)
    search_fields = ('user_email',)
    raw_id_fields = ('case_study', 'payment')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(ResourceBookmark)
class ResourceBookmarkAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_email', 'resource', 'created_at')
    list_filter = ('resource',)
    search_fields = ('user_email',)
    raw_id_fields = ('resource',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'program', 'paper', 'timed', 'total_questions', 'correct_count', 'started_at', 'finished_at')
    list_filter = ('program', 'paper', 'timed')
    search_fields = ('user__email',)
    raw_id_fields = ('user',)
    readonly_fields = ('started_at', 'finished_at', 'created_at')
    date_hierarchy = 'started_at'
    ordering = ('-started_at',)


@admin.register(PracticeAnswer)
class PracticeAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'user', 'order_index', 'chosen_answer', 'is_correct', 'answered_at')
    list_filter = ('is_correct', 'chosen_answer')
    search_fields = ('user__email', 'question_text')
    raw_id_fields = ('session', 'user', 'question')
    readonly_fields = ('answered_at',)
    date_hierarchy = 'answered_at'
    ordering = ('-answered_at',)
