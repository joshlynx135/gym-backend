#!/usr/bin/env bash
# Creates demo data through the API: 5 trainers, 12 members, 40 classes, 36 bookings.
# Usage:  bash scripts/seed_demo.sh            (the server must be running)
#         API=http://localhost:9000 bash scripts/seed_demo.sh
set -euo pipefail

API="${API:-http://localhost:8080}"
JSON="Content-Type: application/json"

# post <path> <json-body>  ->  prints the "id" of the created resource
post() {
  curl -sf -X POST "$API$1" -H "$JSON" -d "$2" | jq -r .id
}

trainers=()
for i in $(seq 1 5); do
  trainers+=("$(post /api/trainers "{\"name\":\"Trainer $i\"}")")
done

members=()
for i in $(seq 1 12); do
  members+=("$(post /api/members "{\"name\":\"Member $i\",\"type\":\"PREMIUM\"}")")
done

classes=()
for i in $(seq 1 40); do
  trainer="${trainers[$(( (i - 1) % 5 ))]}"
  classes+=("$(post /api/classes "{\"name\":\"Class $i\",\"max_capacity\":10,\"trainer_id\":\"$trainer\"}")")
done

# Member j is booked into classes j, j+12 and j+24 (PREMIUM members may hold 3 bookings)
for j in $(seq 0 11); do
  for k in 0 1 2; do
    post "/api/classes/${classes[$(( j + 12 * k ))]}/bookings" "{\"member_id\":\"${members[$j]}\"}" > /dev/null
  done
done

echo "Created ${#trainers[@]} trainers, ${#members[@]} members, ${#classes[@]} classes, 36 bookings."