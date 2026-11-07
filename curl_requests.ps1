<#
  Gym API - curl request suite (Windows PowerShell)

  Exercises every endpoint with curl.exe, including error scenarios.
  Each request states the HTTP status it expects; the script prints
  PASS/FAIL and a summary at the end. It cleans up the data it creates.

  Usage:
    1. Start the server in one terminal:   uv run python main.py
    2. Run this script in another one:     powershell -ExecutionPolicy Bypass -File .\curl_requests.ps1
#>
param([string]$BaseUrl = "http://localhost:8080")

$script:Passed = 0
$script:Failed = 0

function Section([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

# Sends one request with curl.exe, checks the status (and optionally the body), prints the result.
function Invoke-Api {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Method,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][int]$Expect,
        [string]$Body,
        [string]$Contains
    )

    # -s = silent, -w appends the HTTP status code on its own last line
    $curlArgs = @("-s", "-w", "`n%{http_code}", "-X", $Method, "$BaseUrl$Path")
    if ($Body) {
        # "-d @-" tells curl to read the JSON body from stdin (avoids quote-escaping problems)
        $curlArgs += @("-H", "Content-Type: application/json", "-d", "@-")
        $raw = $Body | & curl.exe @curlArgs
    }
    else {
        $raw = & curl.exe @curlArgs
    }

    # Split the output into: response body + status code (the last line)
    $text = ($raw -join "`n")
    $cut = $text.LastIndexOf("`n")
    $status = 0
    $responseBody = ""
    if ($cut -ge 0) {
        $status = [int]$text.Substring($cut + 1)
        $responseBody = $text.Substring(0, $cut)
    }

    $ok = ($status -eq $Expect)
    if ($ok -and $Contains) { $ok = $responseBody.Contains($Contains) }

    if ($ok) { $script:Passed++; $tag = "PASS"; $color = "Green" }
    else { $script:Failed++; $tag = "FAIL"; $color = "Red" }

    Write-Host ("[{0}] {1}" -f $tag, $Name) -ForegroundColor $color
    Write-Host ("       {0} {1} -> {2} (expected {3})" -f $Method, $Path, $status, $Expect)
    if ($Contains) { Write-Host ("       body must contain: {0}" -f $Contains) }
    Write-Host ("       {0}" -f $responseBody)

    $json = $null
    try { $json = $responseBody | ConvertFrom-Json } catch { }
    return [pscustomobject]@{ Status = $status; Json = $json }
}

# ---- Make sure the server is running before we start ----
curl.exe -s -o NUL --max-time 3 "$BaseUrl/api/members"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cannot reach $BaseUrl - start the server first: uv run python main.py" -ForegroundColor Red
    exit 1
}

# =====================================================================
Section "MEMBERS - create"
# =====================================================================
$vera = Invoke-Api "Create PREMIUM member" POST "/api/members" 201 `
    -Body '{"name":"Vera","type":"PREMIUM"}' -Contains '"type":"PREMIUM"'
$vincent = Invoke-Api "Create BASIC member (lowercase type is accepted)" POST "/api/members" 201 `
    -Body '{"name":"Vincent","type":"basic"}' -Contains '"type":"BASIC"'
$sam = Invoke-Api "Create another BASIC member" POST "/api/members" 201 `
    -Body '{"name":"Sam","type":"BASIC"}'
$veraId = $vera.Json.id
$vincentId = $vincent.Json.id
$samId = $sam.Json.id

Invoke-Api "Invalid type -> 400" POST "/api/members" 400 `
    -Body '{"name":"Bob","type":"GOLD"}' -Contains '"error"' | Out-Null
Invoke-Api "Blank name -> 400" POST "/api/members" 400 `
    -Body '{"name":"   ","type":"BASIC"}' -Contains '"error"' | Out-Null
Invoke-Api "Missing field -> 400" POST "/api/members" 400 `
    -Body '{"name":"Bob"}' -Contains '"error"' | Out-Null
Invoke-Api "Malformed JSON -> 400" POST "/api/members" 400 `
    -Body '{this is not json' -Contains '"error"' | Out-Null

# =====================================================================
Section "MEMBERS - read, filter, update"
# =====================================================================
Invoke-Api "List all members" GET "/api/members" 200 | Out-Null
Invoke-Api "Filter members by type=premium" GET "/api/members?type=premium" 200 -Contains "Vera" | Out-Null
Invoke-Api "Invalid filter value -> 400" GET "/api/members?type=gold" 400 -Contains '"error"' | Out-Null
Invoke-Api "Get member by id" GET "/api/members/$veraId" 200 -Contains "Vera" | Out-Null
Invoke-Api "Get unknown member -> 404" GET "/api/members/m-doesnotexist" 404 -Contains '"error"' | Out-Null
Invoke-Api "Replace member (rename)" PUT "/api/members/$vincentId" 200 `
    -Body '{"name":"Vincent S.","type":"BASIC"}' -Contains "Vincent S." | Out-Null
Invoke-Api "Replace unknown member -> 404" PUT "/api/members/m-doesnotexist" 404 `
    -Body '{"name":"X","type":"BASIC"}' | Out-Null
Invoke-Api "Replace with invalid body -> 400" PUT "/api/members/$vincentId" 400 `
    -Body '{"name":"","type":"BASIC"}' | Out-Null

# =====================================================================
Section "CLASSES - create, read, filter, update"
# =====================================================================
$yoga = Invoke-Api "Create class (capacity 5)" POST "/api/classes" 201 `
    -Body '{"name":"Yoga","max_capacity":5}' -Contains '"enrolled":0'
$boxing = Invoke-Api "Create class (capacity 1)" POST "/api/classes" 201 `
    -Body '{"name":"Boxing","max_capacity":1}'
$yogaId = $yoga.Json.id
$boxingId = $boxing.Json.id

Invoke-Api "Capacity 0 -> 400" POST "/api/classes" 400 `
    -Body '{"name":"Bad","max_capacity":0}' -Contains '"error"' | Out-Null
Invoke-Api "Capacity as string -> 400" POST "/api/classes" 400 `
    -Body '{"name":"Bad","max_capacity":"5"}' | Out-Null
Invoke-Api "Missing name -> 400" POST "/api/classes" 400 `
    -Body '{"max_capacity":5}' | Out-Null
Invoke-Api "List all classes" GET "/api/classes" 200 | Out-Null
Invoke-Api "Filter classes by min_capacity=5" GET "/api/classes?min_capacity=5" 200 -Contains "Yoga" | Out-Null
Invoke-Api "Non-numeric min_capacity -> 400" GET "/api/classes?min_capacity=abc" 400 -Contains '"error"' | Out-Null
Invoke-Api "Get class by id" GET "/api/classes/$yogaId" 200 -Contains "Yoga" | Out-Null
Invoke-Api "Get unknown class -> 404" GET "/api/classes/c-doesnotexist" 404 -Contains '"error"' | Out-Null
Invoke-Api "Replace class" PUT "/api/classes/$yogaId" 200 `
    -Body '{"name":"Hot Yoga","max_capacity":5}' -Contains "Hot Yoga" | Out-Null
Invoke-Api "Replace unknown class -> 404" PUT "/api/classes/c-doesnotexist" 404 `
    -Body '{"name":"X","max_capacity":5}' | Out-Null
Invoke-Api "Replace class with invalid capacity -> 400" PUT "/api/classes/$yogaId" 400 `
    -Body '{"name":"Hot Yoga","max_capacity":-3}' | Out-Null

# =====================================================================
Section "BOOKINGS - domain rules"
# =====================================================================
Invoke-Api "Book Vera into Yoga" POST "/api/classes/$yogaId/bookings" 201 `
    -Body (@{ member_id = $veraId } | ConvertTo-Json -Compress) -Contains '"enrolled":1' | Out-Null
Invoke-Api "Double booking -> 409" POST "/api/classes/$yogaId/bookings" 409 `
    -Body (@{ member_id = $veraId } | ConvertTo-Json -Compress) -Contains "already booked" | Out-Null
Invoke-Api "Book Vincent (BASIC) into Yoga" POST "/api/classes/$yogaId/bookings" 201 `
    -Body (@{ member_id = $vincentId } | ConvertTo-Json -Compress) | Out-Null
Invoke-Api "BASIC member over the booking limit (1) -> 409" POST "/api/classes/$boxingId/bookings" 409 `
    -Body (@{ member_id = $vincentId } | ConvertTo-Json -Compress) -Contains "booking limit" | Out-Null
Invoke-Api "Book Vera into Boxing (capacity 1)" POST "/api/classes/$boxingId/bookings" 201 `
    -Body (@{ member_id = $veraId } | ConvertTo-Json -Compress) | Out-Null
Invoke-Api "Book into a full class -> 409" POST "/api/classes/$boxingId/bookings" 409 `
    -Body (@{ member_id = $samId } | ConvertTo-Json -Compress) -Contains "is full" | Out-Null
Invoke-Api "Book unknown member -> 404" POST "/api/classes/$yogaId/bookings" 404 `
    -Body '{"member_id":"m-doesnotexist"}' | Out-Null
Invoke-Api "Book into unknown class -> 404" POST "/api/classes/c-doesnotexist/bookings" 404 `
    -Body (@{ member_id = $samId } | ConvertTo-Json -Compress) | Out-Null
Invoke-Api "Booking without member_id -> 400" POST "/api/classes/$yogaId/bookings" 400 `
    -Body '{}' -Contains '"error"' | Out-Null

Section "RULES THAT SPAN RESOURCES"
Invoke-Api "Lower capacity below enrollment -> 409" PUT "/api/classes/$yogaId" 409 `
    -Body '{"name":"Hot Yoga","max_capacity":1}' -Contains "Cannot lower capacity" | Out-Null
Invoke-Api "Downgrade Vera while over the BASIC limit -> 409" PUT "/api/members/$veraId" 409 `
    -Body '{"name":"Vera","type":"BASIC"}' -Contains "exceeds the new limit" | Out-Null

Section "BOOKINGS - cancel"
Invoke-Api "Cancel Vera's Yoga booking" DELETE "/api/classes/$yogaId/bookings/$veraId" 200 `
    -Contains '"enrolled":1' | Out-Null
Invoke-Api "Cancel again (not enrolled) -> 409" DELETE "/api/classes/$yogaId/bookings/$veraId" 409 `
    -Contains "not enrolled" | Out-Null
Invoke-Api "Cancel for unknown member -> 404" DELETE "/api/classes/$yogaId/bookings/m-doesnotexist" 404 | Out-Null
Invoke-Api "Cancel in unknown class -> 404" DELETE "/api/classes/c-doesnotexist/bookings/$veraId" 404 | Out-Null
Invoke-Api "Downgrade Vera now that she holds exactly 1 booking" PUT "/api/members/$veraId" 200 `
    -Body '{"name":"Vera","type":"BASIC"}' -Contains '"type":"BASIC"' | Out-Null

# =====================================================================
Section "DELETE and cascade"
# =====================================================================
Invoke-Api "Delete class Boxing" DELETE "/api/classes/$boxingId" 200 | Out-Null
Invoke-Api "Delete the same class again -> 404" DELETE "/api/classes/$boxingId" 404 | Out-Null
Invoke-Api "Delete Vincent (booked in Yoga)" DELETE "/api/members/$vincentId" 200 | Out-Null
Invoke-Api "Deleted member is gone -> 404" GET "/api/members/$vincentId" 404 | Out-Null
Invoke-Api "Cascade: Yoga seat was freed" GET "/api/classes/$yogaId" 200 -Contains '"enrolled":0' | Out-Null
Invoke-Api "Delete unknown member -> 404" DELETE "/api/members/m-doesnotexist" 404 | Out-Null

# =====================================================================
Section "ROUTING errors"
# =====================================================================
Invoke-Api "Unknown URL -> 404" GET "/api/nope" 404 -Contains '"error"' | Out-Null
Invoke-Api "Wrong HTTP method -> 405" DELETE "/api/members" 405 -Contains '"error"' | Out-Null

# ---- Clean up whatever is left ----
Section "CLEANUP"
Invoke-Api "Delete Yoga" DELETE "/api/classes/$yogaId" 200 | Out-Null
Invoke-Api "Delete Vera" DELETE "/api/members/$veraId" 200 | Out-Null
Invoke-Api "Delete Sam" DELETE "/api/members/$samId" 200 | Out-Null

# ---- Summary ----
Write-Host ""
$summaryColor = if ($script:Failed -eq 0) { "Green" } else { "Red" }
Write-Host ("Result: {0} passed, {1} failed" -f $script:Passed, $script:Failed) -ForegroundColor $summaryColor
if ($script:Failed -gt 0) { exit 1 }