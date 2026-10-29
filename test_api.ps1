Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "      GYM API - COMPREHENSIVE EDGE-CASE TEST SCRIPT       " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

Write-Host "[1] BASIC CRUD OPERATIONS (POST & GET)" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------"

Write-Host ">>> Creating Basic Member (Vincent)..."
$basic_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"Vincent\`", \`"type\`": \`"BASIC\`"}"
$basic_id = ($basic_json | ConvertFrom-Json).id
Write-Host "Created Member ID: $basic_id" -ForegroundColor DarkGray

Write-Host "`n>>> Creating Premium Member (Vera)..."
$prem_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"Vera\`", \`"type\`": \`"PREMIUM\`"}"
$prem_id = ($prem_json | ConvertFrom-Json).id
Write-Host "Created Member ID: $prem_id" -ForegroundColor DarkGray

Write-Host "`n>>> Creating Yoga Class (Capacity 1)..."
$class_json = curl.exe -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Morning Yoga\`", \`"max_capacity\`": 1}"
$class_id = ($class_json | ConvertFrom-Json).id
Write-Host "Created Class ID: $class_id" -ForegroundColor DarkGray


Write-Host "`n[2] STRESS TESTING: MALFORMED REQUESTS (400 Bad Request)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Sending completely broken/missing JSON syntax:"
$err1 = curl.exe -i -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{name: broken_json_no_quotes"
Write-Host ($err1 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err1 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Sending empty body to POST endpoint:"
$err2 = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json"
Write-Host ($err2 -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n>>> [TEST] Missing required fields (creating class without max_capacity):"
$err3 = curl.exe -i -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Ghost Class\`"}"
Write-Host ($err3 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err3 -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[3] STRESS TESTING: DOMAIN RULES (409 Conflict)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [SETUP] Vera (Premium) books Yoga successfully:"
$book1 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book1 -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Vincent (Basic) tries to book Yoga (Class is full -> 409):"
$book2 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$basic_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book2 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($book2 -split "`r`n`r`n")[1] -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Vera tries to book Yoga AGAIN (Already enrolled -> 409):"
$book3 = curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class_id\`"}"
Write-Host ($book3 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($book3 -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[4] STRESS TESTING: NOT FOUND ERRORS (404 Not Found)" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Accessing a completely fake URL path:"
$err4 = curl.exe -i -s http://localhost:8080/api/ghost-endpoint
Write-Host ($err4 -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n>>> [TEST] Trying to GET a member ID that doesn't exist:"
$err5 = curl.exe -i -s http://localhost:8080/api/members/m-fake999
Write-Host ($err5 -split "`r`n")[0] -ForegroundColor Red
Write-Host ($err5 -split "`r`n`r`n")[1] -ForegroundColor DarkGray


Write-Host "`n[5] UPGRADE & DELETE WORKFLOWS (PUT / DELETE)" -ForegroundColor Cyan
Write-Host "----------------------------------------------------------"

Write-Host ">>> [TEST] Upgrading Vincent to PREMIUM with new name:"
$upgrade = curl.exe -s -X PUT http://localhost:8080/api/members/$basic_id -H "Content-Type: application/json" -d "{\`"type\`": \`"PREMIUM\`", \`"name\`": \`"Vincent S.\`"}"
Write-Host $upgrade -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Verify Vincent's limit is now 3:"
$check_vincent = curl.exe -s http://localhost:8080/api/members/$basic_id
Write-Host $check_vincent -ForegroundColor DarkGray

Write-Host "`n>>> [TEST] Deleting Vera:"
$delete = curl.exe -i -s -X DELETE http://localhost:8080/api/members/$prem_id
Write-Host ($delete -split "`r`n")[0] -ForegroundColor Green

Write-Host "`n>>> [TEST] Verify Vera is deleted (Expect 404):"
$check_vera = curl.exe -i -s http://localhost:8080/api/members/$prem_id
Write-Host ($check_vera -split "`r`n")[0] -ForegroundColor Red

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  ALL TESTS COMPLETED. SERVER DID NOT CRASH.              " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""