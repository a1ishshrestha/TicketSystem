from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from .models import db, Ticket, Notification, Message  # Import models
from datetime import datetime
import pytz

tickets = Blueprint('tickets', __name__)

def convert_to_eastern(timestamp):
    utc = pytz.utc
    eastern = pytz.timezone('US/Eastern')
    utc_timestamp = utc.localize(timestamp)
    return utc_timestamp.astimezone(eastern)

# Dashboard for tickets
@tickets.route('/')
@login_required
def index():
    if current_user.role == 'admin':
        status_filter = request.args.get('status', 'all')
        if status_filter == 'all':
            tickets = Ticket.query.filter_by(archived=False).all()
        else:
            tickets = Ticket.query.filter_by(status=status_filter, archived=False).all()

        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
        for notification in notifications:
            notification.timestamp = convert_to_eastern(notification.timestamp)

        print(f"Fetched notifications for user {current_user.id}: {notifications}")  # Debugging statement
        return render_template('admin_tickets.html', tickets=tickets, notifications=notifications)
    else:
        user_tickets = Ticket.query.filter_by(user_id=current_user.id, archived=False).all()
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
        for notification in notifications:
            notification.timestamp = convert_to_eastern(notification.timestamp)

        print(f"Fetched notifications for user {current_user.id}: {notifications}")  # Debugging statement
        return render_template('index.html', tickets=user_tickets, notifications=notifications)

# Submit a new ticket
@tickets.route('/submit', methods=['GET', 'POST'])
@login_required
def submit_ticket():
    if current_user.role == 'admin':
        flash('Admins cannot submit tickets.')
        return redirect(url_for('tickets.index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        ticket = Ticket(title=title, description=description, user_id=current_user.id)
        db.session.add(ticket)

        # Create a notification for the admin
        notification = Notification(
            user_id=1,  # Assuming admin's ID is 1
            message=f"A new ticket '{title}' has been submitted."
        )
        db.session.add(notification)
        db.session.commit()
        flash('Ticket submitted successfully.')
        return redirect(url_for('tickets.index'))

    return render_template('submit_ticket.html')

# Update ticket statuses (admin only)
@tickets.route('/update_tickets', methods=['POST'])
@login_required
def update_tickets():
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('tickets.index'))

    tickets = Ticket.query.all()
    for ticket in tickets:
        status_key = f'status_{ticket.id}'
        if status_key in request.form:
            new_status = request.form[status_key]
            if ticket.status != new_status:
                ticket.status = new_status

                message = f"The status of your ticket '{ticket.title}' has been updated to '{new_status}'."
                notification = Notification(user_id=ticket.user_id, message=message)
                db.session.add(notification)
                print(f"Creating notification for user {ticket.user_id} with message: {message}")  # Debugging statement

    db.session.commit()
    flash('Ticket statuses updated successfully.')
    return redirect(url_for('tickets.index'))

# Mark a notification as read
@tickets.route('/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('tickets.index'))

    db.session.delete(notification)
    db.session.commit()
    print(f"Marking notification {notification_id} as read for user {current_user.id}")  # Debugging statement
    flash('Notification dismissed successfully.')

    return redirect(url_for('tickets.index'))

# Admin: View/Send Messages for a Ticket
@tickets.route('/tickets/<int:ticket_id>/message', methods=['GET', 'POST'])
@login_required
def send_message(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('tickets.index'))

    if request.method == 'POST':
        content = request.form['message']
        message = Message(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            receiver_id=ticket.user_id,
            content=content
        )
        db.session.add(message)

        notification = Notification(
            user_id=ticket.user_id,
            message=f"You have a new message for ticket '{ticket.title}'."
        )
        db.session.add(notification)
        db.session.commit()
        print(f"Creating notification for user {ticket.user_id} with message: {notification.message}")  # Debugging statement
        flash('Message sent successfully.')
        return redirect(url_for('tickets.send_message', ticket_id=ticket.id))

    messages = Message.query.filter_by(ticket_id=ticket.id).order_by(Message.timestamp).all()
    for message in messages:
        message.local_timestamp = convert_to_eastern(message.timestamp)
    return render_template('admin_ticket_messages.html', ticket=ticket, messages=messages)

# User: Reply to Admin Messages for a Ticket
@tickets.route('/tickets/<int:ticket_id>/reply', methods=['GET', 'POST'])
@login_required
def reply_message(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    if ticket.user_id != current_user.id:
        flash('Access denied.')
        return redirect(url_for('tickets.index'))

    if request.method == 'POST':
        content = request.form['message']
        message = Message(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            receiver_id=1,  # Assuming admin's ID is 1
            content=content
        )
        db.session.add(message)

        # Create a notification for the admin
        notification = Notification(
            user_id=1,  # Assuming admin's ID is 1
            message=f"You have a new reply for ticket '{ticket.title}'."
        )
        db.session.add(notification)
        db.session.commit()
        flash('Reply sent successfully.')
        return redirect(url_for('tickets.reply_message', ticket_id=ticket.id))

    messages = Message.query.filter_by(ticket_id=ticket.id).order_by(Message.timestamp).all()
    for message in messages:
        message.local_timestamp = convert_to_eastern(message.timestamp)
    return render_template('user_ticket_messages.html', ticket=ticket, messages=messages)

# Archive a ticket (admin only)
@tickets.route('/archive/<int:ticket_id>', methods=['POST'])
@login_required
def archive_ticket(ticket_id):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('tickets.index'))

    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.status == 'Resolved':
        ticket.archived = True
        db.session.commit()
        print(f"Ticket {ticket_id} archived successfully.")  # Debugging statement
        flash('Ticket archived successfully.')
    else:
        flash('Only resolved tickets can be archived.')

    return redirect(url_for('tickets.index'))  

# Archive a ticket (admin only)
@tickets.route('/archived')
@login_required
def archived_tickets():
    if current_user.role == 'admin':
        # Fetch archived tickets for the admin
        archived_tickets = Ticket.query.filter_by(archived=True).all()

        # Fetch notifications for the admin
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()

        return render_template('archived_tickets.html', tickets=archived_tickets, notifications=notifications)
    else:
        # Fetch archived tickets for the current user
        user_archived_tickets = Ticket.query.filter_by(user_id=current_user.id, archived=True).all()

        # Fetch notifications for the current user
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()

        return render_template('archived_tickets.html', tickets=user_archived_tickets, notifications=notifications)

    
    

