#!/usr/bin/env bash
# Gym API - curl request suite
#
# Sends real HTTP requests with curl to every endpoint, including error scenarios.
# Each request states the HTTP status it expects. The script prints PASS or FAIL for
# each one and a summary at the end, and deletes the data it created.
#
# Usage:
#   1. docker compose up -d --wait        (PostgreSQL)
#   2. uv run python main.py              (the API; keep it running in another terminal)
#   3. bash curl_requests.sh              (or: BASE_URL=http://host:port bash curl_requests.sh)
#
# Needs only bash, curl and sed. Exit status: 0 = all checks passed, 1 = some failed, 2 = no server.

BASE_URL="${BASE_URL:-http://localhost:8080}"

passed=0
failed=0
last_status=""   # HTTP status of the most recent request
last_body=""     # response body of the most recent request

# Colors only when the output goes to a terminal, so logs stay clean
if [[ -t 1 ]]; then
  GREEN=$'\e[32m'; RED=$'\e[31m'; CYAN=$'\e[36m'; RESET=$'\e[0m'
else
  GREEN=''; RED=''; CYAN=''; RESET=''
fi

section() {
  printf '\n%s=== %s ===%s\n' "$CYAN" "$1" "$RESET"
}

# call <name> <method> <path> <expected status> [json body] [text the response must contain]
call() {
  local name="$1" method="$2" path="$3" expected="$4" body="${5:-}" contains="${6:-}"

  # -s: no progress bar. -w appends the HTTP status code on its own last line.
  local -a args=(-s -w $'\n%{http_code}' -X "$method" "$BASE_URL$path")
  if [[ -n "$body" ]]; then
    args+=(-H "Content-Type: application/json" -d "$body")
  fi

  local response
  response="$(curl "${args[@]}")"
  last_status="${response##*$'\n'}"   # everything after the last newline
  last_body="${response%$'\n'*}"      # everything before the last newline

  local ok=1
  [[ "$last_status" == "$expected" ]] || ok=0
  if [[ -n "$contains" && "$last_body" != *"$contains"* ]]; then
    ok=0
  fi

  if (( ok )); then
    passed=$((passed + 1))
    printf '%s[PASS]%s %s\n' "$GREEN" "$RESET" "$name"
  else
    failed=$((failed + 1))
    printf '%s[FAIL]%s %s\n' "$RED" "$RESET" "$name"
  fi
  printf '       %s %s -> HTTP %s (expected %s)\n' "$method" "$path" "$last_status" "$expected"
  if [[ -n "$contains" ]]; then
    printf '       body must contain: %s\n' "$contains"
  fi
  if (( ${#last_body} > 200 )); then
    printf '       %s...\n' "${last_body:0:200}"
  else
    printf '       %s\n' "$last_body"
  fi
}

# Prints the "id" of the resource in the last response, e.g. {"id":"m-1a2b3c4d", ...}
id_of_last() {
  sed -E 's/^\{"id":"([^"]+)".*/\1/' <<< "$last_body"
}

# JSON bodies that contain ids
booking_body()  { printf '{"member_id":"%s"}' "$1"; }
trainer_body()  { printf '{"trainer_id":"%s"}' "$1"; }
transfer_body() { printf '{"member_id":"%s","from_class_id":"%s","to_class_id":"%s"}' "$1" "$2" "$3"; }

# ---- Make sure the API is running before we start ----
status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE_URL/api/members")"
if [[ "$status" != "200" ]]; then
  echo "Cannot use the API at $BASE_URL (HTTP $status)." >&2
  echo "Start PostgreSQL ('docker compose up -d --wait') and the API ('uv run python main.py') first." >&2
  exit 2
fi

# =====================================================================
section "TRAINERS"
# =====================================================================
call "Create trainer Anna" POST /api/trainers 201 '{"name":"Anna"}' '"name":"Anna"'
ANNA="$(id_of_last)"
call "Create trainer Boris" POST /api/trainers 201 '{"name":"Boris"}'
BORIS="$(id_of_last)"
call "Blank trainer name -> 400" POST /api/trainers 400 '{"name":"   "}' '"error"'
call "Missing trainer name -> 400" POST /api/trainers 400 '{}' '"error"'
call "List trainers" GET /api/trainers 200 '' "$ANNA"
call "Get trainer by id" GET "/api/trainers/$ANNA" 200 '' '"name":"Anna"'
call "Get unknown trainer -> 404" GET /api/trainers/t-doesnotexist 404 '' '"error"'
call "Rename trainer" PUT "/api/trainers/$BORIS" 200 '{"name":"Boris B."}' '"name":"Boris B."'
call "Empty trainer update -> 400" PUT "/api/trainers/$BORIS" 400 '{}' 'At least one field'
call "Update unknown trainer -> 404" PUT /api/trainers/t-doesnotexist 404 '{"name":"X"}' '"error"'

# =====================================================================
section "MEMBERS - create, read, filter, update"
# =====================================================================
call "Create PREMIUM member Vera" POST /api/members 201 '{"name":"Vera","type":"PREMIUM"}' '"type":"PREMIUM"'
VERA="$(id_of_last)"
call "Create BASIC member Sam (lowercase type is accepted)" POST /api/members 201 '{"name":"Sam","type":"basic"}' '"type":"BASIC"'
SAM="$(id_of_last)"
call "Create member Olga" POST /api/members 201 '{"name":"Olga","type":"BASIC"}'
OLGA="$(id_of_last)"
call "Invalid member type -> 400" POST /api/members 400 '{"name":"Bob","type":"GOLD"}' '"error"'
call "Blank member name -> 400" POST /api/members 400 '{"name":"   ","type":"BASIC"}' '"error"'
call "Missing member type -> 400" POST /api/members 400 '{"name":"Bob"}' '"error"'
call "Malformed JSON -> 400" POST /api/members 400 '{this is not json' '"error"'
call "List members" GET /api/members 200 '' "$VERA"
call "Filter members by type=premium" GET "/api/members?type=premium" 200 '' "$VERA"
call "Invalid member filter -> 400" GET "/api/members?type=gold" 400 '' '"error"'
call "Get member by id" GET "/api/members/$VERA" 200 '' '"name":"Vera"'
call "Get unknown member -> 404" GET /api/members/m-doesnotexist 404 '' '"error"'
call "Update only the name (type is kept)" PUT "/api/members/$SAM" 200 '{"name":"Sam S."}' '"type":"BASIC"'
call "Update only the type (name is kept)" PUT "/api/members/$OLGA" 200 '{"type":"premium"}' '"type":"PREMIUM"'
call "Empty member update -> 400" PUT "/api/members/$SAM" 400 '{}' 'At least one field'
call "Update unknown member -> 404" PUT /api/members/m-doesnotexist 404 '{"name":"X"}' '"error"'
call "Update with invalid type -> 400" PUT "/api/members/$SAM" 400 '{"type":"GOLD"}' '"error"'

# =====================================================================
section "CLASSES - create, read, filter, update"
# =====================================================================
call "Create class Yoga with a trainer" POST /api/classes 201 \
  "{\"name\":\"Yoga\",\"max_capacity\":5,\"trainer_id\":\"$ANNA\"}" "\"trainer_id\":\"$ANNA\""
YOGA="$(id_of_last)"
call "Create class Boxing without a trainer (capacity 1)" POST /api/classes 201 \
  '{"name":"Boxing","max_capacity":1}' '"trainer_id":null'
BOXING="$(id_of_last)"
call "Create class Pilates" POST /api/classes 201 '{"name":"Pilates","max_capacity":5}'
PILATES="$(id_of_last)"
call "Capacity 0 -> 400" POST /api/classes 400 '{"name":"Bad","max_capacity":0}' '"error"'
call "Capacity as a string -> 400" POST /api/classes 400 '{"name":"Bad","max_capacity":"5"}' '"error"'
call "Missing class name -> 400" POST /api/classes 400 '{"max_capacity":5}' '"error"'
call "Class with an unknown trainer -> 404" POST /api/classes 404 \
  '{"name":"Ghost","max_capacity":5,"trainer_id":"t-doesnotexist"}' '"error"'
call "List classes" GET /api/classes 200 '' "$YOGA"
call "Filter classes by min_capacity=5" GET "/api/classes?min_capacity=5" 200 '' "$YOGA"
call "Non-numeric min_capacity -> 400" GET "/api/classes?min_capacity=abc" 400 '' '"error"'
call "Filter classes by trainer" GET "/api/classes?trainer_id=$ANNA" 200 '' "$YOGA"
call "Get class by id" GET "/api/classes/$YOGA" 200 '' '"name":"Yoga"'
call "Get unknown class -> 404" GET /api/classes/c-doesnotexist 404 '' '"error"'
call "Invalid include value -> 400" GET "/api/classes?include=nope" 400 '' '"error"'
call "Update only the name (capacity is kept)" PUT "/api/classes/$YOGA" 200 '{"name":"Yoga Flow"}' '"max_capacity":5'
call "Update only the capacity (name is kept)" PUT "/api/classes/$PILATES" 200 '{"max_capacity":8}' '"name":"Pilates"'
call "Empty class update -> 400" PUT "/api/classes/$YOGA" 400 '{}' 'At least one field'
call "Update unknown class -> 404" PUT /api/classes/c-doesnotexist 404 '{"name":"X"}' '"error"'
call "Update with invalid capacity -> 400" PUT "/api/classes/$YOGA" 400 '{"max_capacity":-3}' '"error"'

# =====================================================================
section "BOOKINGS - domain rules"
# =====================================================================
call "Book Sam into Yoga" POST "/api/classes/$YOGA/bookings" 201 "$(booking_body "$SAM")" '"enrolled":1'
call "Double booking -> 409" POST "/api/classes/$YOGA/bookings" 409 "$(booking_body "$SAM")" 'already booked'
call "BASIC member over the booking limit -> 409" POST "/api/classes/$BOXING/bookings" 409 "$(booking_body "$SAM")" 'booking limit'
call "Book Vera into Boxing" POST "/api/classes/$BOXING/bookings" 201 "$(booking_body "$VERA")" '"enrolled":1'
call "Book into a full class -> 409" POST "/api/classes/$BOXING/bookings" 409 "$(booking_body "$OLGA")" 'is full'
call "Book unknown member -> 404" POST "/api/classes/$YOGA/bookings" 404 '{"member_id":"m-doesnotexist"}' '"error"'
call "Book into unknown class -> 404" POST /api/classes/c-doesnotexist/bookings 404 "$(booking_body "$SAM")" '"error"'
call "Booking without member_id -> 400" POST "/api/classes/$YOGA/bookings" 400 '{}' '"error"'
call "Book Vera into Yoga" POST "/api/classes/$YOGA/bookings" 201 "$(booking_body "$VERA")" '"enrolled":2'
call "Lower capacity below enrollment -> 409" PUT "/api/classes/$YOGA" 409 '{"max_capacity":1}' 'Cannot lower capacity'
call "Downgrade a member over the new limit -> 409" PUT "/api/members/$VERA" 409 '{"type":"BASIC"}' 'exceeds the new limit'
call "List classes with trainer and members" GET "/api/classes?include=details" 200 '' "\"trainer\":{\"id\":\"$ANNA\""

# =====================================================================
section "TRANSFER - changes two classes in one transaction"
# =====================================================================
call "Transfer Vera from Boxing to Pilates" POST /api/bookings/transfer 200 \
  "$(transfer_body "$VERA" "$BOXING" "$PILATES")" '"to_class"'
call "BASIC member at the limit can transfer (total stays 1)" POST /api/bookings/transfer 200 \
  "$(transfer_body "$SAM" "$YOGA" "$BOXING")" '"to_class"'
call "Transfer into a full class -> 409" POST /api/bookings/transfer 409 \
  "$(transfer_body "$VERA" "$PILATES" "$BOXING")" 'is full'
call "...and nothing changed: Vera is still in Pilates" GET "/api/classes/$PILATES" 200 '' '"enrolled":1'
call "Transfer from a class the member is not in -> 409" POST /api/bookings/transfer 409 \
  "$(transfer_body "$VERA" "$BOXING" "$YOGA")" 'not enrolled'
call "Transfer to a class the member already attends -> 409" POST /api/bookings/transfer 409 \
  "$(transfer_body "$VERA" "$YOGA" "$PILATES")" 'already booked'
call "Transfer to the same class -> 400" POST /api/bookings/transfer 400 \
  "$(transfer_body "$VERA" "$YOGA" "$YOGA")" 'different classes'
call "Transfer to an unknown class -> 404" POST /api/bookings/transfer 404 \
  "$(transfer_body "$VERA" "$PILATES" "c-doesnotexist")" '"error"'
call "Transfer with a missing field -> 400" POST /api/bookings/transfer 400 \
  "{\"member_id\":\"$VERA\",\"from_class_id\":\"$PILATES\"}" '"error"'

# =====================================================================
section "TRAINER OF A CLASS"
# =====================================================================
call "Assign a trainer to a class" PUT "/api/classes/$PILATES/trainer" 200 "$(trainer_body "$ANNA")" "\"trainer_id\":\"$ANNA\""
call "Assign an unknown trainer -> 404" PUT "/api/classes/$PILATES/trainer" 404 "$(trainer_body t-doesnotexist)" '"error"'
call "Assign a trainer to an unknown class -> 404" PUT /api/classes/c-doesnotexist/trainer 404 "$(trainer_body "$ANNA")" '"error"'
call "Assign without trainer_id -> 400" PUT "/api/classes/$PILATES/trainer" 400 '{}' '"error"'
call "Delete a trainer who still has classes -> 409" DELETE "/api/trainers/$ANNA" 409 '' 'Cannot delete trainer'
call "Remove the trainer from a class" DELETE "/api/classes/$PILATES/trainer" 200 '' '"trainer_id":null'
call "Remove again (none assigned) -> 409" DELETE "/api/classes/$PILATES/trainer" 409 '' 'no trainer'
call "Delete a trainer without classes" DELETE "/api/trainers/$BORIS" 200
call "Deleted trainer is gone -> 404" GET "/api/trainers/$BORIS" 404
call "Delete unknown trainer -> 404" DELETE /api/trainers/t-doesnotexist 404 '' '"error"'

# =====================================================================
section "BOOKINGS - cancel"
# =====================================================================
call "Cancel Vera's Yoga booking" DELETE "/api/classes/$YOGA/bookings/$VERA" 200 '' '"enrolled":0'
call "Cancel again (not enrolled) -> 409" DELETE "/api/classes/$YOGA/bookings/$VERA" 409 '' 'not enrolled'
call "Cancel for an unknown member -> 404" DELETE "/api/classes/$YOGA/bookings/m-doesnotexist" 404 '' '"error"'
call "Cancel in an unknown class -> 404" DELETE "/api/classes/c-doesnotexist/bookings/$VERA" 404 '' '"error"'
call "Downgrade at exactly the new limit (1 booking)" PUT "/api/members/$VERA" 200 '{"type":"BASIC"}' '"type":"BASIC"'

# =====================================================================
section "DELETE and cascade"
# =====================================================================
call "Delete member Sam (booked in Boxing)" DELETE "/api/members/$SAM" 200
call "Cascade: Sam's seat in Boxing was freed" GET "/api/classes/$BOXING" 200 '' '"enrolled":0'
call "Deleted member is gone -> 404" GET "/api/members/$SAM" 404
call "Delete the same member again -> 404" DELETE "/api/members/$SAM" 404 '' '"error"'
call "Delete class Pilates (Vera is booked in it)" DELETE "/api/classes/$PILATES" 200
call "Delete the same class again -> 404" DELETE "/api/classes/$PILATES" 404 '' '"error"'
call "Deleting a class keeps its members" GET "/api/members/$VERA" 200 '' "$VERA"

# =====================================================================
section "ROUTING errors"
# =====================================================================
call "Unknown URL -> 404" GET /api/nope 404 '' '"error"'
call "Wrong HTTP method -> 405" DELETE /api/members 405 '' '"error"'

# =====================================================================
section "CLEANUP"
# =====================================================================
call "Delete class Yoga" DELETE "/api/classes/$YOGA" 200
call "Delete class Boxing" DELETE "/api/classes/$BOXING" 200
call "Delete trainer Anna" DELETE "/api/trainers/$ANNA" 200
call "Delete member Vera" DELETE "/api/members/$VERA" 200
call "Delete member Olga" DELETE "/api/members/$OLGA" 200

# ---- Summary ----
echo
if (( failed == 0 )); then
  printf '%sResult: %d passed, 0 failed%s\n' "$GREEN" "$passed" "$RESET"
  exit 0
fi
printf '%sResult: %d passed, %d failed%s\n' "$RED" "$passed" "$failed" "$RESET"
exit 1