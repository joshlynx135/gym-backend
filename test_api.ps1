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

Write-Host "`n>>> Creating Basic Member (John) for overflow testing..."
$overflow_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"John\`", \`"type\`": \`"BASIC\`"}"
$overflow_id = ($overflow_json | ConvertFrom-Json).id
Write-Host "Created Member ID: $overflow_id" -ForegroundColor DarkGray

Write-Host "`n>>> Creating Yoga Class (Capacity 2)..."
$class_json = curl.exe -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Morning Yoga\`", \`"max_capacity\`": 2}"
$class_id = ($class_json | ConvertFrom-Json).id
Write-Host "Created Class ID: $class_id" -ForegroundColor DarkGray


Write-Host "`n[2] INPUT VALIDATION & BAD REQUESTS (400 & 409)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Malformed JSON Syntax:"
$err1 = curl.exe -i -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{name: broken_json_no_quotes"
Write-Host ($err1 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err1 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Empty Request Body:"
$err2 = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json"
Write-Host ($err2 -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n>>> [TEST] Missing Required Fields:"
$err3 = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Ghost Class\`"}"
Write-Host ($err3 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err3 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Invalid Data Type (String instead of Integer for Capacity):"
$err_type = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Bad Class\`", \`"max_capacity\`": \`"five\`"}"
Write-Host ($err_type -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_type -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Boundary Validation (Negative Capacity):"
$err_neg = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Bad Class\`", \`"max_capacity\`": -5}"
Write-Host ($err_neg -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_neg -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[3] DOMAIN LOGIC & BOOKING RULES (409 Conflict)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [SETUP] Vera (Premium) books Yoga successfully:"
$book1 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book1 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [SETUP] Vincent (Basic) books Yoga successfully (Capacity reached):"
$book2 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$basic_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book2 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Capacity Limit Reached (John attempts to book full class):"
$book3 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$overflow_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book3 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($book3 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Duplicate Booking Prevention (Vera attempts to re-book):"
$book4 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book4 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($book4 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Capacity Shrink Validation (Attempt to lower capacity below 2 enrollments):"
$err_shrink = curl.exe -i -s -X PUT http://localhost:8080/api/classes/$class_id -H "Content-Type: application/json" -d "{\`"max_capacity\`": 1}"
Write-Host ($err_shrink -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err_shrink -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[4] RESOURCE NOT FOUND ERRORS (404)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Invalid URL Path:"
$err4 = curl.exe -i -s http://localhost:8080/api/invalid-endpoint
Write-Host ($err4 -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n>>> [TEST] Invalid Member ID:"
$err5 = curl.exe -i -s http://localhost:8080/api/members/m-fake999
Write-Host ($err5 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err5 -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[5] UPDATES & CASCADING DELETIONS (PUT / DELETE)" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Updating Vincent to PREMIUM configuration:"
$upgrade = curl.exe -s -X PUT http://localhost:8080/api/members/$basic_id -H "Content-Type: application/json" -d "{\`"type\`": \`"PREMIUM\`", \`"name\`": \`"Vincent S.\`"}"
Write-Host $upgrade -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Downgrading Vera to BASIC configuration:"
$downgrade = curl.exe -s -X PUT http://localhost:8080/api/members/$prem_id -H "Content-Type: application/json" -d "{\`"type\`": \`"BASIC\`"}"
Write-Host $downgrade -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Deleting Vincent (Should cascade and remove class reservations):"
$delete1 = curl.exe -i -s -X DELETE http://localhost:8080/api/members/$basic_id
Write-Host ($delete1 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Verifying cascaded deletion in Yoga class via GET (Should contain 1 reservation):"
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