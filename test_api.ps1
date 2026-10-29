Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "1. CREATING RESOURCES (POST)" -ForegroundColor Cyan
Write-Host "========================================="

Write-Host "`n---> Create Basic Member (Limit 1)"
$basic_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"Vincent\`", \`"type\`": \`"BASIC\`"}"
Write-Host $basic_json
$basic_id = ($basic_json | ConvertFrom-Json).id

Write-Host "`n---> Create Premium Member (Limit 3)"
$prem_json = curl.exe -s -X POST http://localhost:8080/api/members -H "Content-Type: application/json" -d "{\`"name\`": \`"Vera\`", \`"type\`": \`"PREMIUM\`"}"
Write-Host $prem_json
$prem_id = ($prem_json | ConvertFrom-Json).id

Write-Host "`n---> Create Yoga Class (Capacity 1)"
$class_json = curl.exe -s -X POST http://localhost:8080/api/classes -H "Content-Type: application/json" -d "{\`"name\`": \`"Morning Yoga\`", \`"max_capacity\`": 1}"
Write-Host $class_json
$class_id = ($class_json | ConvertFrom-Json).id

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "2. LISTING & FILTERING (GET)" -ForegroundColor Cyan
Write-Host "========================================="

Write-Host "`n---> Get all members:"
curl.exe -s http://localhost:8080/api/members

Write-Host "`n---> Get classes with min_capacity >= 1 (Filtering):"
curl.exe -s "http://localhost:8080/api/classes?min_capacity=1"

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "3. DOMAIN BUSINESS RULES" -ForegroundColor Cyan
Write-Host "========================================="

Write-Host "`n---> Vera (Premium) books Yoga (Success - 200 OK):"
curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$prem_id\`", \`"class_id\`": \`"$class_id\`"}"

Write-Host "`n---> Vincent (Basic) tries to book Yoga (Error 409 - Class is full):"
curl.exe -i -s -X POST http://localhost:8080/api/bookings -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$basic_id\`", \`"class_id\`": \`"$class_id\`"}"

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "4. UPDATE & DELETE" -ForegroundColor Cyan
Write-Host "========================================="

Write-Host "`n---> Update Vincent's name to 'Vincent S.' (PUT):"
curl.exe -s -X PUT http://localhost:8080/api/members/$basic_id -H "Content-Type: application/json" -d "{\`"name\`": \`"Vincent S.\`"}"

Write-Host "`n---> Delete Vincent from the gym (DELETE):"
curl.exe -s -X DELETE http://localhost:8080/api/members/$basic_id

Write-Host "`n---> Try to get Vincent after deletion (Error 404 - Not Found):"
curl.exe -i -s http://localhost:8080/api/members/$basic_id