Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "      GYM API - COMPREHENSIVE AUTOMATED TEST SCRIPT       " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

Write-Host "[1] SYSTEM INITIALIZATION (POST)" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------"

Write-Host ">>> Creating Basic Member (Vincent)..."
$basic_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"Vincent\`", \`"type\`": \`"BASIC\`"}"
$basic_id = ($basic_json | ConvertFrom-Json).id
Write-Host "Created Member ID: $basic_id" -ForegroundColor DarkGray

Write-Host "`n>>> Creating Premium Member (Vera)..."
$prem_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"Vera\`", \`"type\`": \`"PREMIUM\`"}"
$prem_id = ($prem_json | ConvertFrom-Json).id
Write-Host "Created Member ID: $prem_id" -ForegroundColor DarkGray

Write-Host "`n>>> Creating Basic Member (John)..."
$overflow_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"John\`", \`"type\`": \`"BASIC\`"}"
$overflow_id = ($overflow_json | ConvertFrom-Json).id
Write-Host "Created Member ID: $overflow_id" -ForegroundColor DarkGray

Write-Host "`n>>> Creating Morning Yoga Class (Capacity 2)..."
$class_json = curl.exe -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Morning Yoga\`", \`"max_capacity\`": 2}"
$class_id = ($class_json | ConvertFrom-Json).id
Write-Host "Created Class ID: $class_id" -ForegroundColor DarkGray

Write-Host "`n>>> Creating Evening Boxing Class (Capacity 5)..."
$class2_json = curl.exe -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Evening Boxing\`", \`"max_capacity\`": 5}"
$class2_id = ($class2_json | ConvertFrom-Json).id
Write-Host "Created Class ID: $class2_id" -ForegroundColor DarkGray


Write-Host "`n[2] INPUT VALIDATION & BAD REQUESTS (400 & 409)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Malformed JSON Syntax (Expect 400):"
$err1 = curl.exe -i -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{name: broken_json_no_quotes"
Write-Host ($err1 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err1 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Non-Object JSON Payload / Array (Expect 400):"
$err_arr = curl.exe -i -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "[1, 2, 3]"
Write-Host ($err_arr -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_arr -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Empty Request Body on POST (Expect 409):"
$err2 = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json"
Write-Host ($err2 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err2 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Empty String Name Validation (Expect 409):"
$err_empty_name = curl.exe -i -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"   \`", \`"type\`": \`"BASIC\`"}"
Write-Host ($err_empty_name -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_empty_name -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Missing Required Fields (Expect 409):"
$err3 = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Ghost Class\`"}"
Write-Host ($err3 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err3 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Invalid Data Type - String for Capacity (Expect 409):"
$err_type = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Bad Class\`", \`"max_capacity\`": \`"five\`"}"
Write-Host ($err_type -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_type -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Boolean Trap - True for Capacity (Expect 409):"
$err_bool = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Bool Class\`", \`"max_capacity\`": true}"
Write-Host ($err_bool -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_bool -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Boundary Validation - Negative Capacity (Expect 409):"
$err_neg = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Bad Class\`", \`"max_capacity\`": -5}"
Write-Host ($err_neg -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_neg -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Invalid Query Parameter Type - min_capacity=abc (Expect 400):"
$err_query = curl.exe -i -s "http://localhost:8080/api/classes?min_capacity=abc"
Write-Host ($err_query -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_query -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Invalid Member Filter Type - type=VIP (Expect 400):"
$err_filter = curl.exe -i -s "http://localhost:8080/api/members?type=VIP"
Write-Host ($err_filter -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_filter -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[3] FILTERING & SINGLE-RESOURCE RETRIEVAL (GET)" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Filtering Members by type=BASIC:"
$basic_list = curl.exe -s "http://localhost:8080/api/members?type=BASIC"
Write-Host $basic_list -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Filtering Classes by min_capacity=4:"
$filtered_classes = curl.exe -s "http://localhost:8080/api/classes?min_capacity=4"
Write-Host $filtered_classes -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Getting Single Member by ID ($basic_id):"
$single_member = curl.exe -s http://localhost:8080/api/members/$basic_id
Write-Host $single_member -ForegroundColor DarkGray


Write-Host "`n[4] DOMAIN LOGIC & BOOKING RULES (409 Conflict)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [SETUP] Vera (Premium) books Morning Yoga and Evening Boxing:"
$book1 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book1 -split "`r`n")[0] -ForegroundColor Green
$book1_b = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class2_id\`"}"
Write-Host ($book1_b -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [SETUP] Vincent (Basic) books Morning Yoga (Class capacity 2/2 reached):"
$book2 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$basic_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book2 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Capacity Limit Reached - John attempts to book full Morning Yoga (Expect 409):"
$book3 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$overflow_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book3 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($book3 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Duplicate Booking Prevention - Vera attempts to re-book Morning Yoga (Expect 409):"
$book4 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book4 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($book4 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Member Booking Limit - Vincent (Basic, limit 1) attempts to book Evening Boxing (Expect 409):"
$book5 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$basic_id\`", \`"class_id\`": \`"$class2_id\`"}"
Write-Host ($book5 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($book5 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Capacity Shrink Validation - Lower Morning Yoga capacity below 2 enrollments (Expect 409):"
$err_shrink = curl.exe -i -s -X PUT http://localhost:8080/api/classes/$class_id -H "Content-Type: application/json" -d "{\`"max_capacity\`": 1}"
Write-Host ($err_shrink -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_shrink -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Downgrade Limit Violation - Downgrade Vera to BASIC while holding 2 active bookings (Expect 409):"
$err_downgrade = curl.exe -i -s -X PUT http://localhost:8080/api/members/$prem_id -H "Content-Type: application/json" -d "{\`"type\`": \`"BASIC\`"}"
Write-Host ($err_downgrade -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_downgrade -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[5] RESOURCE NOT FOUND ERRORS (404)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Invalid URL Path:"
$err4 = curl.exe -i -s http://localhost:8080/api/invalid-endpoint
Write-Host ($err4 -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n>>> [TEST] Invalid Member ID:"
$err5 = curl.exe -i -s http://localhost:8080/api/members/m-fake999
Write-Host ($err5 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err5 -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[6] CANCELLATIONS, UPDATES & CASCADING DELETIONS (PUT / DELETE)" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Canceling Vera's Evening Boxing booking (DELETE /api/bookings):"
$cancel1 = curl.exe -i -s -X DELETE http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class2_id\`"}"
Write-Host ($cancel1 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Attempting to cancel non-existent booking (Expect 409):"
$cancel2 = curl.exe -i -s -X DELETE http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class2_id\`"}"
Write-Host ($cancel2 -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n>>> [TEST] Downgrading Vera to BASIC now that she has 1 active booking (Expect 200):"
$downgrade = curl.exe -s -X PUT http://localhost:8080/api/members/$prem_id -H "Content-Type: application/json" -d "{\`"type\`": \`"BASIC\`"}"
Write-Host $downgrade -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Updating Vincent to PREMIUM configuration:"
$upgrade = curl.exe -s -X PUT http://localhost:8080/api/members/$basic_id -H "Content-Type: application/json" -d "{\`"type\`": \`"PREMIUM\`", \`"name\`": \`"Vincent S.\`"}"
Write-Host $upgrade -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Deleting Vincent (Cascades and removes class reservations):"
$delete1 = curl.exe -i -s -X DELETE http://localhost:8080/api/members/$basic_id
Write-Host ($delete1 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Verifying cascaded deletion in Morning Yoga via GET (Should contain 1 reservation):"
$class_check = curl.exe -s http://localhost:8080/api/classes/$class_id
Write-Host $class_check -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Deleting Vera:"
$delete2 = curl.exe -i -s -X DELETE http://localhost:8080/api/members/$prem_id
Write-Host ($delete2 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Verifying Vera is deleted (Expect 404):"
$check_vera = curl.exe -i -s http://localhost:8080/api/members/$prem_id
Write-Host ($check_vera -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  ALL AUTOMATED TESTS EXECUTED SUCCESSFULLY.              " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""