#!/bin/bash
set -e
echo "==========================================================="
echo "  📚 Library Management System — Resource Provisioning"
echo "==========================================================="

ENDPOINT="http://localhost:4566"
REGION="us-east-1"
AWS="aws --endpoint-url=$ENDPOINT --region $REGION"

# ── 1. DynamoDB Table ────────────────────────────────────────────
echo ""
echo "📦 Creating DynamoDB table [lms-books]..."
$AWS dynamodb create-table \
    --table-name lms-books \
    --attribute-definitions AttributeName=isbn,AttributeType=S \
    --key-schema AttributeName=isbn,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST

echo "⏳ Waiting for table to become active..."
$AWS dynamodb wait table-exists --table-name lms-books

# ── 2. SNS Topic ────────────────────────────────────────────────
echo ""
echo "📡 Creating SNS topic [book-events-topic]..."
TOPIC_ARN=$($AWS sns create-topic \
    --name book-events-topic \
    --query "TopicArn" --output text)
echo "   Topic ARN: $TOPIC_ARN"

# ── 3. SQS Queue ────────────────────────────────────────────────
echo ""
echo "📬 Creating SQS queue [inventory-update-queue]..."
QUEUE_URL=$($AWS sqs create-queue \
    --queue-name inventory-update-queue \
    --query "QueueUrl" --output text)
echo "   Queue URL: $QUEUE_URL"

QUEUE_ARN=$($AWS sqs get-queue-attributes \
    --queue-url "$QUEUE_URL" \
    --attribute-names QueueArn \
    --query "Attributes.QueueArn" --output text)
echo "   Queue ARN: $QUEUE_ARN"

# ── 4. SNS → SQS Subscription ──────────────────────────────────
echo ""
echo "🔗 Subscribing SQS queue to SNS topic..."
$AWS sns subscribe \
    --topic-arn "$TOPIC_ARN" \
    --protocol sqs \
    --notification-endpoint "$QUEUE_ARN"

# ── 5. Seed Book Catalog ────────────────────────────────────────
echo ""
echo "📖 Seeding book catalog with sample data..."

seed_book() {
    $AWS dynamodb put-item --table-name lms-books --item "$1"
}

seed_book '{"isbn":{"S":"978-0132350884"},"title":{"S":"Clean Code"},"author":{"S":"Robert C. Martin"},"genre":{"S":"Software Engineering"},"published_year":{"N":"2008"},"total_copies":{"N":"4"},"available_copies":{"N":"4"},"borrowers":{"L":[]},"description":{"S":"A handbook of agile software craftsmanship that teaches writing clean, maintainable code."}}'

seed_book '{"isbn":{"S":"978-0201633610"},"title":{"S":"Design Patterns"},"author":{"S":"Gang of Four"},"genre":{"S":"Software Engineering"},"published_year":{"N":"1994"},"total_copies":{"N":"3"},"available_copies":{"N":"3"},"borrowers":{"L":[]},"description":{"S":"The classic reference on reusable object-oriented software design patterns."}}'

seed_book '{"isbn":{"S":"978-0135957059"},"title":{"S":"The Pragmatic Programmer"},"author":{"S":"David Thomas & Andrew Hunt"},"genre":{"S":"Software Engineering"},"published_year":{"N":"2019"},"total_copies":{"N":"5"},"available_copies":{"N":"5"},"borrowers":{"L":[]},"description":{"S":"Timeless advice on becoming a better programmer with practical tips and techniques."}}'

seed_book '{"isbn":{"S":"978-0262033848"},"title":{"S":"Introduction to Algorithms"},"author":{"S":"Thomas H. Cormen"},"genre":{"S":"Computer Science"},"published_year":{"N":"2009"},"total_copies":{"N":"3"},"available_copies":{"N":"3"},"borrowers":{"L":[]},"description":{"S":"The comprehensive reference on algorithms covering sorting, graphs, dynamic programming, and more."}}'

seed_book '{"isbn":{"S":"978-0262510875"},"title":{"S":"Structure and Interpretation of Computer Programs"},"author":{"S":"Harold Abelson & Gerald Sussman"},"genre":{"S":"Computer Science"},"published_year":{"N":"1996"},"total_copies":{"N":"2"},"available_copies":{"N":"2"},"borrowers":{"L":[]},"description":{"S":"A foundational text exploring computation through Scheme programming."}}'

seed_book '{"isbn":{"S":"978-0134685991"},"title":{"S":"Refactoring"},"author":{"S":"Martin Fowler"},"genre":{"S":"Software Engineering"},"published_year":{"N":"2018"},"total_copies":{"N":"4"},"available_copies":{"N":"4"},"borrowers":{"L":[]},"description":{"S":"Improving the design of existing code through systematic refactoring techniques."}}'

seed_book '{"isbn":{"S":"978-0596517748"},"title":{"S":"JavaScript: The Good Parts"},"author":{"S":"Douglas Crockford"},"genre":{"S":"Programming Languages"},"published_year":{"N":"2008"},"total_copies":{"N":"3"},"available_copies":{"N":"3"},"borrowers":{"L":[]},"description":{"S":"A deep dive into the elegant and powerful core features of JavaScript."}}'

seed_book '{"isbn":{"S":"978-1491950296"},"title":{"S":"Programming Rust"},"author":{"S":"Jim Blandy & Jason Orendorff"},"genre":{"S":"Programming Languages"},"published_year":{"N":"2021"},"total_copies":{"N":"2"},"available_copies":{"N":"2"},"borrowers":{"L":[]},"description":{"S":"A comprehensive guide to safe systems programming with Rust."}}'

seed_book '{"isbn":{"S":"978-0984782857"},"title":{"S":"Cracking the Coding Interview"},"author":{"S":"Gayle Laakmann McDowell"},"genre":{"S":"Career"},"published_year":{"N":"2015"},"total_copies":{"N":"5"},"available_copies":{"N":"5"},"borrowers":{"L":[]},"description":{"S":"189 programming questions and solutions for technical interview preparation."}}'

seed_book '{"isbn":{"S":"978-0201835953"},"title":{"S":"The Mythical Man-Month"},"author":{"S":"Frederick P. Brooks Jr."},"genre":{"S":"Software Engineering"},"published_year":{"N":"1995"},"total_copies":{"N":"3"},"available_copies":{"N":"3"},"borrowers":{"L":[]},"description":{"S":"Legendary essays on software engineering and project management."}}'

echo ""
echo "==========================================================="
echo "  ✅ All LMS resources provisioned successfully!"
echo "  📚 10 books seeded into catalog"
echo "  📡 SNS → SQS event pipeline active"
echo "==========================================================="
