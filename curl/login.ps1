param(
    [Parameter(Mandatory = $true)]
    [string]$Username,

    [Parameter(Mandatory = $true)]
    [string]$Password,

    [Alias("ReportOutput")]
    [string]$HomeOutput,

    [string]$OverviewOutput,

    [string]$SearchMessageOutput,

    [string]$MessageDetailsOutput,

    [string]$ResponseOutput,

    [string]$MessageText
)

$ErrorActionPreference = "Stop"

function ConvertTo-CurlConfigValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    return $Value.Replace("\", "\\").Replace('"', '\"')
}

function Join-CurlResponseText {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Response
    )

    if ($Response -is [System.Array]) {
        return [string]::Join("`n", [string[]]$Response)
    }

    return [string]$Response
}

function Get-HttpStatusCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Metadata
    )

    $match = [regex]::Match($Metadata, 'HTTP_STATUS=(\d+)')
    if ($match.Success) {
        return [int]$match.Groups[1].Value
    }

    return $null
}

function Invoke-CurlTextRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [string[]]$Headers = @(),

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $curlArgs = @(
        "--silent",
        "--show-error",
        "--cookie-jar", $script:cookieJar,
        "--cookie", $script:cookieJar
    )

    foreach ($header in $Headers) {
        $curlArgs += @("--header", $header)
    }

    $curlArgs += $Url

    $response = & curl.exe @curlArgs
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }

    return Join-CurlResponseText -Response $response
}

function Invoke-CurlMetadataRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,

        [string[]]$Headers = @(),

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $curlArgs = @(
        "--silent",
        "--show-error",
        "--cookie-jar", $script:cookieJar,
        "--cookie", $script:cookieJar,
        "--output", "NUL",
        "--write-out", "HTTP_STATUS=%{http_code}`nCONTENT_TYPE=%{content_type}`nSIZE_DOWNLOAD=%{size_download}`nREDIRECT_URL=%{redirect_url}`n"
    )

    foreach ($header in $Headers) {
        $curlArgs += @("--header", $header)
    }

    $curlArgs += $Url

    $metadata = & curl.exe @curlArgs
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }

    return Join-CurlResponseText -Response $metadata
}

function Invoke-CurlConfigRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RequestKey,

        [Parameter(Mandatory = $true)]
        [string]$Url,

        [Parameter(Mandatory = $true)]
        [string[]]$Headers,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath,

        [Parameter(Mandatory = $true)]
        [string]$HeadersOutputPath,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $configPath = Join-Path $script:scriptDir ("precom_{0}.curlrc" -f $RequestKey)
    $configLines = @(
        "silent",
        "show-error",
        "compressed",
        ('cookie-jar = "{0}"' -f (ConvertTo-CurlConfigValue -Value $script:cookieJar)),
        ('cookie = "{0}"' -f (ConvertTo-CurlConfigValue -Value $script:cookieJar)),
        ('url = "{0}"' -f (ConvertTo-CurlConfigValue -Value $Url))
    )

    foreach ($header in $Headers) {
        $configLines += ('header = "{0}"' -f (ConvertTo-CurlConfigValue -Value $header))
    }

    $configLines += ('output = "{0}"' -f (ConvertTo-CurlConfigValue -Value $OutputPath))

    Set-Content -LiteralPath $configPath -Value $configLines

    try {
        $metadata = & curl.exe `
            --config $configPath `
            --dump-header $HeadersOutputPath `
            --write-out "HTTP_STATUS=%{http_code}`nCONTENT_TYPE=%{content_type}`nSIZE_DOWNLOAD=%{size_download}`nREDIRECT_URL=%{redirect_url}`n"
        if ($LASTEXITCODE -ne 0) {
            throw $FailureMessage
        }

        return Join-CurlResponseText -Response $metadata
    }
    finally {
        if (Test-Path $configPath) {
            Remove-Item -LiteralPath $configPath -Force
        }
    }
}

function Invoke-CurlConfigFormRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RequestKey,

        [Parameter(Mandatory = $true)]
        [string]$Url,

        [Parameter(Mandatory = $true)]
        [string[]]$Headers,

        [Parameter(Mandatory = $true)]
        [string]$FormData,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath,

        [Parameter(Mandatory = $true)]
        [string]$HeadersOutputPath,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $configPath = Join-Path $script:scriptDir ("precom_{0}.curlrc" -f $RequestKey)
    $configLines = @(
        "silent",
        "show-error",
        "compressed",
        ('cookie-jar = "{0}"' -f (ConvertTo-CurlConfigValue -Value $script:cookieJar)),
        ('cookie = "{0}"' -f (ConvertTo-CurlConfigValue -Value $script:cookieJar)),
        'request = "POST"',
        ('url = "{0}"' -f (ConvertTo-CurlConfigValue -Value $Url))
    )

    foreach ($header in $Headers) {
        $configLines += ('header = "{0}"' -f (ConvertTo-CurlConfigValue -Value $header))
    }

    $configLines += ('data = "{0}"' -f (ConvertTo-CurlConfigValue -Value $FormData))
    $configLines += ('output = "{0}"' -f (ConvertTo-CurlConfigValue -Value $OutputPath))

    Set-Content -LiteralPath $configPath -Value $configLines

    try {
        $metadata = & curl.exe `
            --config $configPath `
            --dump-header $HeadersOutputPath `
            --write-out "HTTP_STATUS=%{http_code}`nCONTENT_TYPE=%{content_type}`nSIZE_DOWNLOAD=%{size_download}`nREDIRECT_URL=%{redirect_url}`n"
        if ($LASTEXITCODE -ne 0) {
            throw $FailureMessage
        }

        return Join-CurlResponseText -Response $metadata
    }
    finally {
        if (Test-Path $configPath) {
            Remove-Item -LiteralPath $configPath -Force
        }
    }
}

function Ensure-CultureCookie {
    $cultureCookie = ".AspNetCore.Culture"
    $cultureCookieValue = "c%3Dnl-NL%7Cuic%3Dnl-NL"
    $cookieLines = Get-Content -LiteralPath $script:cookieJar -ErrorAction SilentlyContinue
    if (-not ($cookieLines | Select-String -SimpleMatch $cultureCookie -Quiet)) {
        Add-Content -LiteralPath $script:cookieJar -Value "portal.pre-com.nl`tFALSE`t/`tFALSE`t0`t$cultureCookie`t$cultureCookieValue"
        Write-Host "Added missing culture cookie to cookie jar."
    }
}

function Resolve-SearchUrlFromOverviewHtml {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OverviewHtmlPath,

        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,

        [string]$GroupIdOverride
    )

    $overviewHtml = Get-Content -LiteralPath $OverviewHtmlPath -Raw

    $groupIdMatch = [regex]::Match($overviewHtml, 'id="GroupId"[^>]*value="([^"]+)"')
    $fromMatch = [regex]::Match($overviewHtml, 'id="From"[^>]*value="([^"]+)"')
    $toMatch = [regex]::Match($overviewHtml, 'id="To"[^>]*value="([^"]+)"')
    $workingDayMatch = [regex]::Match($overviewHtml, 'id="PeriodPartSelection"[^>]*value="([^"]+)"')

    if (-not $groupIdMatch.Success) {
        throw "Could not find GroupId in the overview HTML."
    }
    if (-not $fromMatch.Success -or -not $toMatch.Success) {
        throw "Could not find From/To values in the overview HTML."
    }

    $dateFormats = @(
        "d-M-yyyy HH:mm:ss",
        "dd-M-yyyy HH:mm:ss",
        "d-MM-yyyy HH:mm:ss",
        "dd-MM-yyyy HH:mm:ss"
    )
    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $dateStyles = [System.Globalization.DateTimeStyles]::None

    $fromDate = $null
    foreach ($dateFormat in $dateFormats) {
        try {
            $fromDate = [datetime]::ParseExact($fromMatch.Groups[1].Value, $dateFormat, $culture, $dateStyles)
            break
        }
        catch {
        }
    }
    if (-not $fromDate) {
        throw "Could not parse From value '$($fromMatch.Groups[1].Value)' from the overview HTML."
    }

    $toDate = $null
    foreach ($dateFormat in $dateFormats) {
        try {
            $toDate = [datetime]::ParseExact($toMatch.Groups[1].Value, $dateFormat, $culture, $dateStyles)
            break
        }
        catch {
        }
    }
    if (-not $toDate) {
        throw "Could not parse To value '$($toMatch.Groups[1].Value)' from the overview HTML."
    }
    $groupId = if ([string]::IsNullOrWhiteSpace($GroupIdOverride)) { $groupIdMatch.Groups[1].Value } else { $GroupIdOverride }
    $workingDay = if ($workingDayMatch.Success) { $workingDayMatch.Groups[1].Value } else { "" }

    $fromIso = $fromDate.ToString("yyyy-MM-ddTHH:mm:ss")
    $toIso = $toDate.ToString("yyyy-MM-ddTHH:mm:ss")
    $workingDayQueryValue = if ([string]::IsNullOrWhiteSpace($workingDay) -or $workingDay -eq "0") { "" } else { $workingDay }

    $searchUriBuilder = [System.UriBuilder]::new("$BaseUrl/ReportMessage/Search")
    $searchUriBuilder.Query = "GroupId=$([uri]::EscapeDataString($groupId))&From=$([uri]::EscapeDataString($fromIso))&To=$([uri]::EscapeDataString($toIso))&WorkingDay=$([uri]::EscapeDataString($workingDayQueryValue))"

    return $searchUriBuilder.Uri.AbsoluteUri
}

function Get-GroupCandidatesFromOverviewHtml {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OverviewHtmlPath
    )

    $overviewHtml = Get-Content -LiteralPath $OverviewHtmlPath -Raw
    $result = @()

    $dataSourceMatch = [regex]::Match($overviewHtml, '"dataSource":(\[[\s\S]*?\]),"value"')
    if ($dataSourceMatch.Success) {
        try {
            $items = $dataSourceMatch.Groups[1].Value | ConvertFrom-Json
            foreach ($item in @($items)) {
                if ($null -ne $item.Value -and -not [string]::IsNullOrWhiteSpace([string]$item.Value)) {
                    $result += [pscustomobject]@{
                        GroupId = [string]$item.Value
                        Name = [string]$item.Text
                    }
                }
            }
        }
        catch {
        }
    }

    if ($result.Count -eq 0) {
        $groupIdMatch = [regex]::Match($overviewHtml, 'id="GroupId"[^>]*value="([^"]+)"')
        if (-not $groupIdMatch.Success) {
            throw "Could not extract any GroupId candidates from the overview HTML."
        }

        $result += [pscustomobject]@{
            GroupId = [string]$groupIdMatch.Groups[1].Value
            Name = "Default"
        }
    }

    return ,$result
}

function Resolve-MessageDetailsUrlFromMessage {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Message,

        [Parameter(Mandatory = $true)]
        [string]$BaseUrl
    )

    if ($null -eq $Message.MsgInLogID -or [string]::IsNullOrWhiteSpace([string]$Message.MsgInLogID)) {
        throw "Cannot resolve MessageDetails URL because MsgInLogID is missing."
    }

    $queryParts = @(
        "messageInLogId=$([uri]::EscapeDataString([string]$Message.MsgInLogID))"
    )

    if ($null -ne $Message.IncidentLogID -and -not [string]::IsNullOrWhiteSpace([string]$Message.IncidentLogID)) {
        $queryParts += "incidentLogID=$([uri]::EscapeDataString([string]$Message.IncidentLogID))"
    }

    $messageDetailsUriBuilder = [System.UriBuilder]::new("$BaseUrl/ReportMessage/MessageDetails")
    $messageDetailsUriBuilder.Query = [string]::Join("&", $queryParts)

    return $messageDetailsUriBuilder.Uri.AbsoluteUri
}

function Resolve-SearchMessageUrlFromHtml {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HtmlPath,

        [Parameter(Mandatory = $true)]
        [string]$BaseUrl
    )

    $html = Get-Content -LiteralPath $HtmlPath -Raw
    $match = [regex]::Match($html, '/PreCom/ReportMessage/SearchMessage\?[^"]+')
    if (-not $match.Success) {
        throw "Could not find the SearchMessage URL in the report search HTML."
    }

    $relativeUrl = $match.Value.Replace('\u0026', '&')
    return [System.Uri]::new([System.Uri]$BaseUrl, $relativeUrl).AbsoluteUri
}

function Resolve-MessageDetailsUrlFromSearchMessageJson {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SearchMessageJsonPath,

        [Parameter(Mandatory = $true)]
        [string]$BaseUrl
    )

    $searchMessageJson = Get-Content -LiteralPath $SearchMessageJsonPath -Raw | ConvertFrom-Json
    $firstMessage = @($searchMessageJson.Data) | Select-Object -First 1

    if (-not $firstMessage) {
        throw "SearchMessage did not contain any rows to resolve MessageDetails from."
    }

    $queryParts = @(
        "messageInLogId=$([uri]::EscapeDataString([string]$firstMessage.MsgInLogID))"
    )

    if ($null -ne $firstMessage.IncidentLogID -and -not [string]::IsNullOrWhiteSpace([string]$firstMessage.IncidentLogID)) {
        $queryParts += "incidentLogID=$([uri]::EscapeDataString([string]$firstMessage.IncidentLogID))"
    }

    $messageDetailsUriBuilder = [System.UriBuilder]::new("$BaseUrl/ReportMessage/MessageDetails")
    $messageDetailsUriBuilder.Query = [string]::Join("&", $queryParts)

    return [pscustomobject]@{
        Url = $messageDetailsUriBuilder.Uri.AbsoluteUri
        FirstMessage = $firstMessage
    }
}

function Resolve-SearchResponseUrlFromMessage {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Message,

        [Parameter(Mandatory = $true)]
        [string]$BaseUrl
    )

    if ($null -eq $Message.MsgInLogID -or [string]::IsNullOrWhiteSpace([string]$Message.MsgInLogID)) {
        throw "Cannot resolve SearchResponse URL because MsgInLogID is missing."
    }

    $searchResponseUriBuilder = [System.UriBuilder]::new("$BaseUrl/ReportUser/SearchResponse")
    $searchResponseUriBuilder.Query = "msgInLogId=$([uri]::EscapeDataString([string]$Message.MsgInLogID))"

    return $searchResponseUriBuilder.Uri.AbsoluteUri
}

function Write-ResponseSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [string]$Metadata,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath,

        [Parameter(Mandatory = $true)]
        [string]$HeadersOutputPath
    )

    Write-Host "$Label response saved to: $OutputPath"
    Write-Host "$Label headers saved to: $HeadersOutputPath"

    Write-Host ""
    Write-Host "$Label response metadata:"
    $Metadata

    if (Test-Path $OutputPath) {
        $outputFile = Get-Item -LiteralPath $OutputPath
        Write-Host "$Label response size: $($outputFile.Length) bytes"
    }
}

function Cleanup-GeneratedFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$FilesToDelete,

        [Parameter(Mandatory = $true)]
        [string[]]$FilesToKeep
    )

    $keepSet = @{}
    foreach ($keep in $FilesToKeep) {
        if (-not [string]::IsNullOrWhiteSpace($keep)) {
            $resolvedKeep = [System.IO.Path]::GetFullPath($keep).ToLowerInvariant()
            $keepSet[$resolvedKeep] = $true
        }
    }

    foreach ($file in $FilesToDelete) {
        if ([string]::IsNullOrWhiteSpace($file)) {
            continue
        }

        $resolvedFile = [System.IO.Path]::GetFullPath($file).ToLowerInvariant()
        if ($keepSet.ContainsKey($resolvedFile)) {
            continue
        }

        if (Test-Path -LiteralPath $file) {
            Remove-Item -LiteralPath $file -Force
        }
    }
}

$baseUrl = "https://portal.pre-com.nl/PreCom"
$loginUrl = "$baseUrl/Account/Login"
$postLoginUrl = "$baseUrl/Account/PostLogin"
$homeUrl = $baseUrl
$navigationNodesUrl = "$baseUrl/Navigation/GetNodes"
$navigationModulesUrl = "$baseUrl/Navigation/GetModules"
$overviewUrl = "$baseUrl/ReportMessage/Overview"
$script:scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:cookieJar = Join-Path $script:scriptDir "precom_cookies.txt"
if ([string]::IsNullOrWhiteSpace($HomeOutput)) {
    $HomeOutput = Join-Path $script:scriptDir "precom_home.html"
}
$homeHeadersOutput = [System.IO.Path]::ChangeExtension($HomeOutput, ".headers.txt")
if ([string]::IsNullOrWhiteSpace($OverviewOutput)) {
    $OverviewOutput = Join-Path $script:scriptDir "precom_report_overview.html"
}
$overviewHeadersOutput = [System.IO.Path]::ChangeExtension($OverviewOutput, ".headers.txt")
$searchHtmlOutput = Join-Path $script:scriptDir "precom_report_search.html"
$searchHtmlHeadersOutput = [System.IO.Path]::ChangeExtension($searchHtmlOutput, ".headers.txt")
if ([string]::IsNullOrWhiteSpace($SearchMessageOutput)) {
    $SearchMessageOutput = Join-Path $script:scriptDir "precom_report_searchmessage.json"
}
$searchMessageHeadersOutput = [System.IO.Path]::ChangeExtension($SearchMessageOutput, ".headers.txt")
if ([string]::IsNullOrWhiteSpace($MessageDetailsOutput)) {
    $MessageDetailsOutput = Join-Path $script:scriptDir "precom_report_messagedetails.html"
}
$messageDetailsHeadersOutput = [System.IO.Path]::ChangeExtension($MessageDetailsOutput, ".headers.txt")
if ([string]::IsNullOrWhiteSpace($ResponseOutput)) {
    $ResponseOutput = Join-Path $script:scriptDir "precom_report_response.json"
}
$responseHeadersOutput = [System.IO.Path]::ChangeExtension($ResponseOutput, ".headers.txt")

$homeRequestHeaders = @(
    'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language: nl,en;q=0.9',
    'Connection: keep-alive',
    'DNT: 1',
    'Sec-Fetch-Dest: document',
    'Sec-Fetch-Mode: navigate',
    'Sec-Fetch-Site: none',
    'Sec-Fetch-User: ?1',
    'Upgrade-Insecure-Requests: 1',
    'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0',
    'sec-ch-ua: "Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile: ?0',
    'sec-ch-ua-platform: "Windows"'
)

$overviewRequestHeaders = @(
    'Accept: text/html, */*; q=0.01',
    'Accept-Language: nl,en;q=0.9',
    'Connection: keep-alive',
    'DNT: 1',
    'Sec-Fetch-Dest: empty',
    'Sec-Fetch-Mode: cors',
    'Sec-Fetch-Site: same-origin',
    'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0',
    'X-Requested-With: XMLHttpRequest',
    'sec-ch-ua: "Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile: ?0',
    'sec-ch-ua-platform: "Windows"'
)

$searchMessageRequestHeaders = @(
    'Accept: application/json, text/javascript, */*; q=0.01',
    'Accept-Language: nl,en;q=0.9',
    'Connection: keep-alive',
    'DNT: 1',
    'Sec-Fetch-Dest: empty',
    'Sec-Fetch-Mode: cors',
    'Sec-Fetch-Site: same-origin',
    'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0',
    'X-Requested-With: XMLHttpRequest',
    'sec-ch-ua: "Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile: ?0',
    'sec-ch-ua-platform: "Windows"'
)

$responseRequestHeaders = @(
    'Accept: */*',
    'Accept-Language: nl,en;q=0.9',
    'Connection: keep-alive',
    'Content-Type: application/x-www-form-urlencoded; charset=UTF-8',
    'DNT: 1',
    'Origin: https://portal.pre-com.nl',
    'Sec-Fetch-Dest: empty',
    'Sec-Fetch-Mode: cors',
    'Sec-Fetch-Site: same-origin',
    'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0',
    'X-Requested-With: XMLHttpRequest',
    'sec-ch-ua: "Microsoft Edge";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    'sec-ch-ua-mobile: ?0',
    'sec-ch-ua-platform: "Windows"'
)

if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    throw "curl.exe is not available in PATH."
}

Write-Host "Using cookie jar: $script:cookieJar"
if (Test-Path $script:cookieJar) {
    Remove-Item -LiteralPath $script:cookieJar -Force
}

Write-Host ""
if ([string]::IsNullOrWhiteSpace($Username) -or [string]::IsNullOrWhiteSpace($Password)) {
    Write-Host "Username or Password is empty. Login will likely fail."
    Write-Host ""
}

Write-Host "Step 1: GET login page"
& curl.exe --silent --show-error `
    --cookie-jar $script:cookieJar `
    --cookie $script:cookieJar `
    $loginUrl | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to fetch login page."
}

Write-Host "Step 2: POST login form"
$response = & curl.exe --silent --show-error `
    --cookie-jar $script:cookieJar `
    --cookie $script:cookieJar `
    --header "Content-Type: application/x-www-form-urlencoded" `
    --header "Referer: $loginUrl" `
    --header "X-Requested-With: XMLHttpRequest" `
    --data-urlencode "UserName=$Username" `
    --data-urlencode "Password=$Password" `
    $postLoginUrl
if ($LASTEXITCODE -ne 0) {
    throw "Failed to post login form."
}

Write-Host ""
Write-Host "Login response:"
$response

Write-Host ""
$loginSucceeded = $false
if ($response -match '"Succesfully":true') {
    Write-Host "Status: login looks successful."
    $loginSucceeded = $true
}
elseif ($response -match '"Succesfully":false') {
    Write-Host "Status: login failed according to server response."
}
elseif ($response -match 'Succesfully') {
    Write-Host "Status: login response contains 'Succesfully', but could not match true/false exactly."
}
else {
    Write-Host "Status: response does not contain the expected 'Succesfully' field."
}

Write-Host ""
Write-Host "Saved cookies:"
if (Test-Path $script:cookieJar) {
    Get-Content -LiteralPath $script:cookieJar
}
else {
    Write-Host "Cookie jar was not created."
}

Write-Host ""
Write-Host "Step 3: GET portal homepage"

if (-not $loginSucceeded) {
    Write-Host "Skipping homepage request because login was not successful."
}
else {
    Ensure-CultureCookie

    Write-Host "Home URL:"
    Write-Host "  $homeUrl"

    $homeMeta = Invoke-CurlConfigRequest `
        -RequestKey "home_request" `
        -Url $homeUrl `
        -Headers $homeRequestHeaders `
        -OutputPath $HomeOutput `
        -HeadersOutputPath $homeHeadersOutput `
        -FailureMessage "Failed to fetch homepage response."
    Write-ResponseSummary `
        -Label "Homepage" `
        -Metadata $homeMeta `
        -OutputPath $HomeOutput `
        -HeadersOutputPath $homeHeadersOutput

    $homeStatus = Get-HttpStatusCode -Metadata $homeMeta
    if ($homeStatus -ne 200) {
        throw "Homepage request returned HTTP $homeStatus."
    }

    Write-Host ""
    Write-Host "Step 4: Resolve report navigation"

    $nodesResponse = Invoke-CurlTextRequest `
        -Url $navigationNodesUrl `
        -FailureMessage "Failed to fetch navigation nodes."
    $nodes = [object[]](ConvertFrom-Json $nodesResponse)
    if ($nodes.Count -eq 0) {
        throw "No nodes were returned by /PreCom/Navigation/GetNodes."
    }

    $activeNode = $nodes[0]
    $resolvedNodeId = [int]$activeNode.id
    Write-Host "Resolved nodeId: $resolvedNodeId ($($activeNode.name))"

    $topModulesResponse = Invoke-CurlTextRequest `
        -Url $navigationModulesUrl `
        -FailureMessage "Failed to fetch top-level modules."
    $topModules = [object[]](ConvertFrom-Json $topModulesResponse)
    $reportModule = $topModules | Where-Object { $_.name -eq "Rapportage" } | Select-Object -First 1
    if (-not $reportModule) {
        $availableTopModules = ($topModules | ForEach-Object { $_.name }) -join ", "
        throw "Could not find 'Rapportage' in top-level modules. Available modules: $availableTopModules"
    }

    $resolvedReportMenuId = [int]$reportModule.id
    Write-Host "Resolved rapportage menuId: $resolvedReportMenuId"

    $childModulesUrl = "{0}?id={1}" -f $navigationModulesUrl, $resolvedReportMenuId
    $childModulesResponse = Invoke-CurlTextRequest `
        -Url $childModulesUrl `
        -FailureMessage "Failed to fetch child modules for 'Rapportage'."
    $childModules = [object[]](ConvertFrom-Json $childModulesResponse)
    $reportMessageModule = $childModules | Where-Object { $_.name -eq "Rapportage per bericht" } | Select-Object -First 1
    if (-not $reportMessageModule) {
        $availableChildModules = ($childModules | ForEach-Object { $_.name }) -join ", "
        throw "Could not find 'Rapportage per bericht' under 'Rapportage'. Available child modules: $availableChildModules"
    }

    $resolvedReportMessageMenuId = [int]$reportMessageModule.id
    Write-Host "Resolved rapportage per bericht menuId: $resolvedReportMessageMenuId"

    Write-Host ""
    Write-Host "Step 5: Load report module context"
    $moduleLoadUrl = "{0}/Module/Load?nodeId={1}&menuId={2}" -f $baseUrl, $resolvedNodeId, $resolvedReportMessageMenuId
    Write-Host "Module load URL:"
    Write-Host "  $moduleLoadUrl"

    $moduleLoadMeta = Invoke-CurlMetadataRequest `
        -Url $moduleLoadUrl `
        -FailureMessage "Failed to load report module context."
    Write-Host ""
    Write-Host "Report module context metadata:"
    $moduleLoadMeta

    $moduleLoadStatus = Get-HttpStatusCode -Metadata $moduleLoadMeta
    if ($moduleLoadStatus -ne 200) {
        throw "Report module context request returned HTTP $moduleLoadStatus."
    }

    Write-Host ""
    Write-Host "Step 6: GET ReportMessage/Overview"
    Write-Host "Overview URL:"
    Write-Host "  $overviewUrl"

    $overviewMeta = Invoke-CurlConfigRequest `
        -RequestKey "overview_request" `
        -Url $overviewUrl `
        -Headers $overviewRequestHeaders `
        -OutputPath $OverviewOutput `
        -HeadersOutputPath $overviewHeadersOutput `
        -FailureMessage "Failed to fetch overview response."
    Write-ResponseSummary `
        -Label "Overview" `
        -Metadata $overviewMeta `
        -OutputPath $OverviewOutput `
        -HeadersOutputPath $overviewHeadersOutput

    $overviewStatus = Get-HttpStatusCode -Metadata $overviewMeta
    if ($overviewStatus -ne 200) {
        throw "Overview request returned HTTP $overviewStatus."
    }

    Write-Host ""
    Write-Host "Step 7: Search message in report groups"
    $groupCandidates = Get-GroupCandidatesFromOverviewHtml -OverviewHtmlPath $OverviewOutput
    Write-Host "Resolved report groups: $($groupCandidates.Count)"

    $selectedMessage = $null
    $selectedGroup = $null
    $selectedSearchMessageJson = $null

    foreach ($groupCandidate in $groupCandidates) {
        Write-Host ""
        Write-Host "Trying group '$($groupCandidate.Name)' (GroupId=$($groupCandidate.GroupId))"

        $searchUrl = Resolve-SearchUrlFromOverviewHtml `
            -OverviewHtmlPath $OverviewOutput `
            -BaseUrl $homeUrl `
            -GroupIdOverride $groupCandidate.GroupId

        Write-Host "Search URL:"
        Write-Host "  $searchUrl"

        $searchHtmlMeta = Invoke-CurlConfigRequest `
            -RequestKey "search_request" `
            -Url $searchUrl `
            -Headers $overviewRequestHeaders `
            -OutputPath $searchHtmlOutput `
            -HeadersOutputPath $searchHtmlHeadersOutput `
            -FailureMessage "Failed to fetch report search response."

        $searchStatus = Get-HttpStatusCode -Metadata $searchHtmlMeta
        if ($searchStatus -ne 200) {
            throw "Search request returned HTTP $searchStatus for GroupId $($groupCandidate.GroupId)."
        }

        $searchMessageUrl = Resolve-SearchMessageUrlFromHtml `
            -HtmlPath $searchHtmlOutput `
            -BaseUrl $homeUrl
        Write-Host "SearchMessage URL:"
        Write-Host "  $searchMessageUrl"

        $searchMessageMeta = Invoke-CurlConfigRequest `
            -RequestKey "searchmessage_request" `
            -Url $searchMessageUrl `
            -Headers $searchMessageRequestHeaders `
            -OutputPath $SearchMessageOutput `
            -HeadersOutputPath $searchMessageHeadersOutput `
            -FailureMessage "Failed to fetch SearchMessage response."

        $searchMessageStatus = Get-HttpStatusCode -Metadata $searchMessageMeta
        if ($searchMessageStatus -ne 200) {
            throw "SearchMessage request returned HTTP $searchMessageStatus for GroupId $($groupCandidate.GroupId)."
        }

        $searchMessageJson = Get-Content -LiteralPath $SearchMessageOutput -Raw | ConvertFrom-Json
        $searchMessageRows = @($searchMessageJson.Data).Count
        Write-Host "SearchMessage rows: $searchMessageRows"

        if ([string]::IsNullOrWhiteSpace($MessageText)) {
            $selectedMessage = @($searchMessageJson.Data) | Select-Object -First 1
        }
        else {
            $selectedMessage = @($searchMessageJson.Data) | Where-Object {
                $null -ne $_.Text -and ([string]$_.Text).IndexOf($MessageText, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
            } | Select-Object -First 1
        }

        if ($null -ne $selectedMessage) {
            $selectedGroup = $groupCandidate
            $selectedSearchMessageJson = $searchMessageJson
            break
        }
    }

    if ($null -eq $selectedMessage) {
        if ([string]::IsNullOrWhiteSpace($MessageText)) {
            throw "No SearchMessage rows were found in any configured group."
        }

        throw "Could not find a message containing '$MessageText' in any configured group."
    }

    Write-Host ""
    if ([string]::IsNullOrWhiteSpace($MessageText)) {
        Write-Host "Selected first SearchMessage row from group '$($selectedGroup.Name)'."
    }
    else {
        Write-Host "Found matching message in group '$($selectedGroup.Name)' (GroupId=$($selectedGroup.GroupId))."
    }

    Write-Host "Selected message: MsgInLogID=$($selectedMessage.MsgInLogID), MsgInID=$($selectedMessage.MsgInID), IncidentLogID=$($selectedMessage.IncidentLogID)"

    $searchMessageRows = @($selectedSearchMessageJson.Data).Count
    Write-Host "SearchMessage total: $($selectedSearchMessageJson.Total)"

    if ($searchMessageRows -gt 0) {
        Write-Host ""
        Write-Host "Step 9: GET ReportMessage/MessageDetails for selected SearchMessage row"
        $messageDetailsUrl = Resolve-MessageDetailsUrlFromMessage `
            -Message $selectedMessage `
            -BaseUrl $homeUrl

        Write-Host "MessageDetails URL:"
        Write-Host "  $messageDetailsUrl"

        $messageDetailsMeta = Invoke-CurlConfigRequest `
            -RequestKey "messagedetails_request" `
            -Url $messageDetailsUrl `
            -Headers $overviewRequestHeaders `
            -OutputPath $MessageDetailsOutput `
            -HeadersOutputPath $messageDetailsHeadersOutput `
            -FailureMessage "Failed to fetch MessageDetails response."
        Write-ResponseSummary `
            -Label "MessageDetails" `
            -Metadata $messageDetailsMeta `
            -OutputPath $MessageDetailsOutput `
            -HeadersOutputPath $messageDetailsHeadersOutput

        $messageDetailsStatus = Get-HttpStatusCode -Metadata $messageDetailsMeta
        if ($messageDetailsStatus -ne 200) {
            throw "MessageDetails request returned HTTP $messageDetailsStatus."
        }

        Write-Host ""
        Write-Host "Step 10: POST ReportUser/SearchResponse for selected SearchMessage row"
        $responseUrl = Resolve-SearchResponseUrlFromMessage `
            -Message $selectedMessage `
            -BaseUrl $homeUrl

        Write-Host "SearchResponse URL:"
        Write-Host "  $responseUrl"

        $responseMeta = Invoke-CurlConfigFormRequest `
            -RequestKey "response_request" `
            -Url $responseUrl `
            -Headers $responseRequestHeaders `
            -FormData "sort=&group=&filter=" `
            -OutputPath $ResponseOutput `
            -HeadersOutputPath $responseHeadersOutput `
            -FailureMessage "Failed to fetch SearchResponse response."
        Write-ResponseSummary `
            -Label "SearchResponse" `
            -Metadata $responseMeta `
            -OutputPath $ResponseOutput `
            -HeadersOutputPath $responseHeadersOutput

        $responseStatus = Get-HttpStatusCode -Metadata $responseMeta
        if ($responseStatus -ne 200) {
            throw "SearchResponse request returned HTTP $responseStatus."
        }

        $responseJson = Get-Content -LiteralPath $ResponseOutput -Raw | ConvertFrom-Json
        $responseRows = @($responseJson.Data).Count
        Write-Host "SearchResponse rows: $responseRows"
        Write-Host "SearchResponse total: $($responseJson.Total)"

        Cleanup-GeneratedFiles `
            -FilesToDelete @(
                $script:cookieJar,
                $HomeOutput,
                $homeHeadersOutput,
                $OverviewOutput,
                $overviewHeadersOutput,
                $searchHtmlOutput,
                $searchHtmlHeadersOutput,
                $SearchMessageOutput,
                $searchMessageHeadersOutput,
                $messageDetailsHeadersOutput,
                $responseHeadersOutput
            ) `
            -FilesToKeep @(
                $MessageDetailsOutput,
                $ResponseOutput
            )

        Write-Host "Cleanup completed. Kept files:"
        Write-Host "  $MessageDetailsOutput"
        Write-Host "  $ResponseOutput"
    }
}
