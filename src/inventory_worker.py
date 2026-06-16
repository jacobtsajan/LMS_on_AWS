"""
Inventory Worker — Background SQS poller for the LMS event pipeline.

Continuously long-polls the inventory-update-queue for book checkout/return
events published via SNS. Logs each event as an audit trail, demonstrating
the decoupled, event-driven architecture.
"""
import json
import os
import signal
import sys
import time

# ── Path setup ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.aws_config import get_sqs_client, SQS_QUEUE_URL

# ── Globals ──────────────────────────────────────────────────────
sqs = get_sqs_client()
running = True


def graceful_shutdown(signum, frame):
    """Handle SIGTERM/SIGINT for clean Docker stop."""
    global running
    print('\n🛑 Shutdown signal received. Finishing current poll...')
    running = False


signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)


def wait_for_queue():
    """Block until the SQS queue is provisioned by the bootstrap script."""
    max_retries = 40
    for i in range(max_retries):
        try:
            sqs.get_queue_attributes(
                QueueUrl=SQS_QUEUE_URL,
                AttributeNames=['QueueArn'],
            )
            print('✅ SQS queue "inventory-update-queue" is ready!')
            return
        except Exception:
            print(f'⏳ Waiting for queue... ({i + 1}/{max_retries})')
            time.sleep(3)
    raise RuntimeError('SQS queue not ready after timeout')


def process_message(message):
    """Parse and log an incoming SNS→SQS event message."""
    try:
        # SNS wraps messages in an envelope when delivering to SQS
        envelope = json.loads(message['Body'])
        payload = json.loads(envelope.get('Message', '{}'))

        action = payload.get('action', 'UNKNOWN')
        isbn = payload.get('isbn', 'N/A')
        borrower = payload.get('borrower_name', 'N/A')
        timestamp = payload.get('timestamp', 'N/A')

        icon = '📕' if action == 'CHECKOUT' else '📗' if action == 'RETURN' else '📘'

        print(f'\n{icon} ── Event Received ──────────────────────────')
        print(f'   Action:    {action}')
        print(f'   ISBN:      {isbn}')
        print(f'   Borrower:  {borrower}')
        print(f'   Timestamp: {timestamp}')
        print(f'   ────────────────────────────────────────────')

        return True
    except (json.JSONDecodeError, KeyError) as e:
        print(f'⚠️  Failed to parse message: {e}')
        return False


def poll_loop():
    """Main polling loop — long-polls SQS and processes messages."""
    print('\n👂 Listening for inventory events on SQS...')
    print('   (Borrow or return a book via the frontend to see events here)\n')

    while running:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=10,           # Long-poll for efficiency
                VisibilityTimeout=30,
            )

            messages = response.get('Messages', [])
            for msg in messages:
                success = process_message(msg)
                if success:
                    # Acknowledge and remove from queue
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=msg['ReceiptHandle'],
                    )
                    print('   ✅ Message acknowledged and removed from queue')

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'⚠️  Polling error: {e}')
            time.sleep(5)

    print('👋 Inventory Worker shut down cleanly.')


# ── Main ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('⚙️  LMS Inventory Worker starting...')
    wait_for_queue()
    poll_loop()
