from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from dashboard.models import User, SupportTicket, UserNotification, AdminNotification
from .utils import admin_required

# =================================================================
# 🎧 إدارة الدعم الفني والبلاغات
# =================================================================
@admin_required
def support_tickets_management(request):
    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '')

        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        old_status = ticket.status 
        
        ticket.status = new_status
        ticket.admin_notes = admin_notes
        ticket.save()

        # إرسال إشعار للمستخدم إذا تغيرت الحالة أو تمت إضافة ملاحظة
        if old_status != new_status or admin_notes:
            status_dict = dict(SupportTicket.STATUS_CHOICES)
            status_ar = status_dict.get(new_status, new_status)
            
            notif_message = f"تم تحديث حالة بلاغك إلى: {status_ar}."
            if admin_notes:
                notif_message += f"\nملاحظة الإدارة: {admin_notes}"

            UserNotification.objects.create(
                user=ticket.user,
                title=f"تحديث بخصوص البلاغ #{ticket.id}",
                message=notif_message
            )

        messages.success(request, f'تم تحديث البلاغ رقم #{ticket.id} وإرسال إشعار للمستخدم بنجاح.')
        return redirect('support_tickets_management')

    # جلب جميع التذاكر وعرضها
    all_tickets = SupportTicket.objects.select_related('user').order_by('-created_at')
    
    context = {
        'tickets': all_tickets,
        'pending_count': all_tickets.filter(status='pending').count(),
        'in_progress_count': all_tickets.filter(status='in_progress').count(),
        'resolved_count': all_tickets.filter(status='resolved').count(),
    }
    return render(request, 'dashboard/support_tickets.html', context)


# =================================================================
# 📢 مركز الإشعارات (إرسال إشعارات للمستخدمين)
# =================================================================
@admin_required
def notifications_management(request):
    if request.method == 'POST':
        target = request.POST.get('target')
        title = request.POST.get('title')
        message = request.POST.get('message')

        users_to_notify = []
        if target == 'all':
            users_to_notify = User.objects.all()
        elif target == 'doctors':
            users_to_notify = User.objects.filter(role='doctor')
        elif target == 'patients':
            users_to_notify = User.objects.filter(role='patient')

        # استخدام bulk_create لإنشاء الإشعارات دفعة واحدة (أسرع وأفضل للأداء)
        notifications = [
            UserNotification(user=u, title=title, message=message) for u in users_to_notify
        ]
        UserNotification.objects.bulk_create(notifications)

        messages.success(request, f'تم إرسال الإشعار إلى {len(users_to_notify)} مستخدم بنجاح!')
        return redirect('notifications_management')

    recent_notifications = UserNotification.objects.select_related('user').order_by('-created_at')[:50]
    
    context = {
        'recent_notifications': recent_notifications,
        'total_users': User.objects.count(),
    }
    return render(request, 'dashboard/notifications_management.html', context)


# =================================================================
# 🔔 تحديث حالة إشعار الإدارة (Ajax)
# =================================================================
@admin_required
def mark_notification_read(request, notif_id):
    if request.method == 'POST':
        try:
            # نتأكد أن الإشعار يخص المدير الحالي (لأسباب أمنية)
            notif = AdminNotification.objects.get(id=notif_id, admin=request.user)
            notif.is_read = True
            notif.save()
            return JsonResponse({'status': 'success'})
        except AdminNotification.DoesNotExist:
            return JsonResponse({'status': 'error'}, status=404)
    return JsonResponse({'status': 'invalid method'}, status=400)