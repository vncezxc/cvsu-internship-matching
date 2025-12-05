from django.contrib import admin
from .models import ChatRoom, Message

class MessageInline(admin.TabularInline):
    """Inline admin for Message model."""
    model = Message
    extra = 0
    readonly_fields = ('sender', 'content', 'timestamp')
    fields = ('sender', 'content', 'timestamp', 'read_by')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class ChatRoomAdmin(admin.ModelAdmin):
    """Admin for ChatRoom model."""
    list_display = ('name', 'get_participants', 'created_at', 'get_message_count')
    search_fields = ('name',)
    filter_horizontal = ('participants',)
    inlines = [MessageInline]
    
    def get_participants(self, obj):
        return ", ".join([p.username for p in obj.participants.all()])
    get_participants.short_description = 'Participants'
    
    def get_message_count(self, obj):
        return obj.messages.count()
    get_message_count.short_description = 'Messages'

class MessageAdmin(admin.ModelAdmin):
    """Admin for Message model."""
    list_display = ('sender', 'content_preview', 'room', 'timestamp', 'is_read')
    list_filter = ('timestamp', 'sender')
    search_fields = ('content', 'sender__username', 'room__name')
    filter_horizontal = ('read_by',)
    readonly_fields = ('sender', 'room', 'content', 'timestamp')
    
    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_preview.short_description = 'Content'
    
    def has_add_permission(self, request):
        return False

# Register models
admin.site.register(ChatRoom, ChatRoomAdmin)
admin.site.register(Message, MessageAdmin)
