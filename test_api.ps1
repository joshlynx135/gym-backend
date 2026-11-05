Write-Host "========================================="
Write-Host "  FASTAPI GYM API - AUTOMATED TEST SUITE "
Write-Host "========================================="
Write-Host ""

$BASE_URL = "http://localhost:8080/api"

Write-Host "1. [SUCCESS] Creating Premium Member..."
$memberRes = curl.exe -s -X POST "$BASE_URL/members" -H "Content-Type: application/json" -d "{\`"name\`": \`"Vincent\`", \`"type\`": \`"PREMIUM\`"}"
Write-Host $memberRes
# Extract ID (simple string manipulation for powershell)
$memberId = ($memberRes | Select-String -Pattern '"id":"(m-[a-f0-9]+)"' | % { $_.Matches.Groups[1].Value })
Write-Host ""

Write-Host "2. [SUCCESS] Creating Workout Class (Capacity: 1)..."
$classRes = curl.exe -s -X POST "$BASE_URL/classes" -H "Content-Type: application/json" -d "{\`"name\`": \`"Yoga\`", \`"max_capacity\`": 1}"
Write-Host $classRes
$classId = ($classRes | Select-String -Pattern '"id":"(c-[a-f0-9]+)"' | % { $_.Matches.Groups[1].Value })
Write-Host ""

Write-Host "3. [SUCCESS] Booking Class..."
curl.exe -s -X POST "$BASE_URL/bookings" -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$memberId\`", \`"class_id\`": \`"$classId\`"}"
Write-Host ""
Write-Host ""

Write-Host "4. [ERROR 409] Booking Full Class (Rule Violation)..."
$member2Res = curl.exe -s -X POST "$BASE_URL/members" -H "Content-Type: application/json" -d "{\`"name\`": \`"Vera\`", \`"type\`": \`"BASIC\`"}"
$member2Id = ($member2Res | Select-String -Pattern '"id":"(m-[a-f0-9]+)"' | % { $_.Matches.Groups[1].Value })
curl.exe -s -i -X POST "$BASE_URL/bookings" -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$member2Id\`", \`"class_id\`": \`"$classId\`"}"
Write-Host ""
Write-Host ""

Write-Host "5. [ERROR 422] Pydantic Validation Error (Negative Capacity)..."
curl.exe -s -i -X POST "$BASE_URL/classes" -H "Content-Type: application/json" -d "{\`"name\`": \`"Crossfit\`", \`"max_capacity\`": -5}"
Write-Host ""
Write-Host ""

Write-Host "6. [SUCCESS] Cancelling Booking & Deleting Member..."
curl.exe -s -X DELETE "$BASE_URL/bookings" -H "Content-Type: application/json" -d "{\`"member_id\`": \`"$memberId\`", \`"class_id\`": \`"$classId\`"}"
Write-Host ""
curl.exe -s -X DELETE "$BASE_URL/members/$memberId"
Write-Host ""
Write-Host ""
Write-Host "========================================="
Write-Host "         TEST SUITE COMPLETE             "
Write-Host "========================================="
