"""
LMS API Server — Flask application serving the Library Management System.

Endpoints:
  GET  /              → Frontend dashboard
  GET  /api/books     → List all books
  POST /api/borrow    → Borrow a book (decrements copies, publishes SNS event)
  POST /api/return    → Return a book (increments copies, publishes SNS event)
"""
import json
import os
import sys
import time
from decimal import Decimal

from flask import Flask, request, jsonify
from flask_cors import CORS

# ── Path setup so imports work both locally and in Docker ────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.aws_config import (
    get_dynamodb_resource, get_sns_client,
    SNS_TOPIC_ARN, TABLE_NAME,
)

# ── Flask app ────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(
    __name__,
    static_folder=os.path.join(project_root, 'frontend'),
    static_url_path='',
)
CORS(app)

# ── AWS clients ──────────────────────────────────────────────────
dynamodb = get_dynamodb_resource()
table = dynamodb.Table(TABLE_NAME)
sns = get_sns_client()


# ── Helpers ──────────────────────────────────────────────────────
class DecimalEncoder(json.JSONEncoder):
    """Encode Decimal values returned by DynamoDB into JSON-safe types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def json_response(data, status=200):
    """Return a Flask response with proper JSON encoding for Decimals."""
    return app.response_class(
        response=json.dumps(data, cls=DecimalEncoder),
        status=status,
        mimetype='application/json',
    )


def wait_for_table():
    """Block until the DynamoDB table is provisioned by the bootstrap script."""
    max_retries = 40
    for i in range(max_retries):
        try:
            table.load()
            # Also verify seed data exists
            resp = table.scan(Limit=1)
            if resp.get('Count', 0) > 0:
                print('✅ DynamoDB table "lms-books" is ready with seed data!')
                return
            raise Exception('Table exists but no data yet')
        except Exception:
            print(f'⏳ Waiting for infrastructure... ({i + 1}/{max_retries})')
            time.sleep(3)
    raise RuntimeError('Infrastructure not ready after timeout')


def publish_event(action, isbn, borrower_name):
    """Publish a borrow/return event to the SNS topic."""
    payload = {
        'action': action,
        'isbn': isbn,
        'borrower_name': borrower_name,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(payload),
        Subject=f'LMS-{action}',
    )
    print(f'📡 Published {action} event for ISBN {isbn}')


# ── Routes ───────────────────────────────────────────────────────
@app.route('/')
def index():
    """Serve the frontend dashboard."""
    return app.send_static_file('index.html')


@app.route('/api/books', methods=['GET'])
def get_books():
    """Return all books in the catalog."""
    response = table.scan()
    items = response.get('Items', [])
    # Sort by title for consistent display
    items.sort(key=lambda b: b.get('title', ''))
    return json_response(items)


@app.route('/api/borrow', methods=['POST'])
def borrow_book():
    """
    Borrow a book: decrement available_copies, add borrower to list,
    and publish a CHECKOUT event to SNS.
    """
    data = request.get_json(force=True)
    isbn = data.get('isbn', '').strip()
    borrower = data.get('borrower_name', '').strip()

    if not isbn or not borrower:
        return jsonify({'error': 'isbn and borrower_name are required'}), 400

    # Fetch current book state
    resp = table.get_item(Key={'isbn': isbn})
    book = resp.get('Item')
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    if int(book.get('available_copies', 0)) <= 0:
        return jsonify({'error': 'No copies available'}), 409

    borrowers = book.get('borrowers', [])
    if borrower in borrowers:
        return jsonify({'error': f'"{borrower}" already has this book checked out'}), 409

    # Update DynamoDB — decrement copies and add borrower
    borrowers.append(borrower)
    table.update_item(
        Key={'isbn': isbn},
        UpdateExpression='SET available_copies = available_copies - :one, borrowers = :b',
        ConditionExpression='available_copies > :zero',
        ExpressionAttributeValues={':one': 1, ':b': borrowers, ':zero': 0},
    )

    # Publish event to SNS → SQS pipeline
    publish_event('CHECKOUT', isbn, borrower)

    return jsonify({'message': f'"{book["title"]}" checked out to {borrower}'}), 200


@app.route('/api/return', methods=['POST'])
def return_book():
    """
    Return a book: increment available_copies, remove borrower from list,
    and publish a RETURN event to SNS.
    """
    data = request.get_json(force=True)
    isbn = data.get('isbn', '').strip()
    borrower = data.get('borrower_name', '').strip()

    if not isbn or not borrower:
        return jsonify({'error': 'isbn and borrower_name are required'}), 400

    resp = table.get_item(Key={'isbn': isbn})
    book = resp.get('Item')
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    borrowers = book.get('borrowers', [])
    if borrower not in borrowers:
        return jsonify({'error': f'"{borrower}" does not have this book checked out'}), 409

    # Update DynamoDB — increment copies and remove borrower
    borrowers.remove(borrower)
    table.update_item(
        Key={'isbn': isbn},
        UpdateExpression='SET available_copies = available_copies + :one, borrowers = :b',
        ExpressionAttributeValues={':one': 1, ':b': borrowers},
    )

    # Publish event to SNS → SQS pipeline
    publish_event('RETURN', isbn, borrower)

    return jsonify({'message': f'"{book["title"]}" returned by {borrower}'}), 200


# ── Main ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('📚 LMS API Server starting...')
    wait_for_table()
    print(f'🚀 Server running at http://0.0.0.0:3000')
    app.run(host='0.0.0.0', port=3000, debug=False)
