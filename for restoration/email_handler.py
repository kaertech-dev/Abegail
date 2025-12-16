# email_handler.py
# Handles email sending functionality

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import re

# Email Configuration
SMTP_SERVER = "smtp-mail.outlook.com"  # Change based on your email provider
SMTP_PORT = 587
SENDER_EMAIL = "ranedez@kaertech.com"
SENDER_PASSWORD = "Natnat15"

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def send_email(recipient_email, subject, message_body):
    """
    Send an email to the specified recipient
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject line
        message_body: Content of the email
        
    Returns:
        dict: Success status and message
    """
    try:
        # Validate email
        if not is_valid_email(recipient_email):
            return {
                'success': False,
                'error': 'Invalid email address format'
            }
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S")
        
        # Add body
        msg.attach(MIMEText(message_body, 'plain'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        
        # Login
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        return {
            'success': True,
            'message': f'Email sent successfully to {recipient_email}'
        }
        
    except smtplib.SMTPAuthenticationError:
        return {
            'success': False,
            'error': 'Email authentication failed. Check your email credentials.'
        }
    except smtplib.SMTPException as e:
        return {
            'success': False,
            'error': f'SMTP error: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to send email: {str(e)}'
        }

def parse_email_request(message):
    """
    Parse user message to extract email details
    Expected formats:
    - "send email to john@example.com subject: Hello body: How are you?"
    - "email john@example.com about Meeting with message: Let's meet tomorrow"
    - "send to john@example.com: Hello, this is a test"
    
    Returns:
        dict: Parsed email details or None if not an email request
    """
    message_lower = message.lower()
    
    # Check if it's an email request
    if not any(phrase in message_lower for phrase in ['send email', 'email to', 'send to', 'email about']):
        return None
    
    result = {
        'recipient': None,
        'subject': None,
        'body': None
    }
    
    # Extract email address
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_pattern, message)
    if email_match:
        result['recipient'] = email_match.group(0)
    
    # Extract subject
    subject_patterns = [
        r'subject:\s*(.+?)(?:\s+body:|\s+message:|\s+with message:|\s*$)',
        r'about\s+(.+?)(?:\s+body:|\s+message:|\s+with message:|\s*$)'
    ]
    
    for pattern in subject_patterns:
        subject_match = re.search(pattern, message, re.IGNORECASE)
        if subject_match:
            result['subject'] = subject_match.group(1).strip()
            break
    
    # Extract body/message
    body_patterns = [
        r'body:\s*(.+?)$',
        r'message:\s*(.+?)$',
        r'with message:\s*(.+?)$',
        r':\s*(.+?)$'  # Fallback: everything after colon
    ]
    
    for pattern in body_patterns:
        body_match = re.search(pattern, message, re.IGNORECASE)
        if body_match:
            body_text = body_match.group(1).strip()
            # Don't use the body if it's the same as subject
            if body_text != result['subject']:
                result['body'] = body_text
                break
    
    # Default subject if not provided
    if not result['subject']:
        result['subject'] = 'Message from Abegail AI Assistant'
    
    # Default body if not provided
    if not result['body']:
        result['body'] = 'No message content provided.'
    
    return result if result['recipient'] else None

def needs_email_action(message):
    """Check if the message is requesting to send an email"""
    message_lower = message.lower()
    
    email_keywords = [
        'send email',
        'email to',
        'send to',
        'email about',
        'send message to',
        'compose email'
    ]
    
    return any(keyword in message_lower for keyword in email_keywords)

def format_email_confirmation(recipient, subject, body):
    """Format a confirmation message for the user"""
    return f"""📧 **Email Details:**

**To:** {recipient}
**Subject:** {subject}
**Message:**
{body}

Would you like me to send this email? (Reply 'yes' to confirm)"""

def get_email_help():
    """Return help text for email functionality"""
    return """📧 **Email Feature Guide**

I can send emails for you! Here's how:

**Basic Format:**
`send email to recipient@example.com subject: Your Subject body: Your message`

**Examples:**

1. **Full format:**
   `send email to john@company.com subject: Meeting Request body: Let's schedule a meeting for tomorrow at 2 PM`

2. **Short format:**
   `email john@company.com about Project Update with message: The project is completed`

3. **Simple format:**
   `send to jane@example.com: Hello, how are you?`

**Notes:**
- Email addresses must be valid
- Subject is optional (defaults to "Message from Abegail AI Assistant")
- The message body is the main content you want to send

**Setup Required:**
To use this feature, configure your email credentials in `email_handler.py`:
- SENDER_EMAIL: Your email address
- SENDER_PASSWORD: Your app password (not regular password)

For Gmail users:
1. Enable 2-factor authentication
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Use that App Password in the configuration"""