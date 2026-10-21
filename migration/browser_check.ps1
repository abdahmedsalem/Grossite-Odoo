param([int]$DebugPort = 9233, [switch]$LiveReadOnly)
$ErrorActionPreference = 'Stop'
$baseUrl = if ($LiveReadOnly) { 'http://localhost:8073' } else { 'http://localhost:8074' }
$artifactPrefix = if ($LiveReadOnly) { 'live-' } else { '' }
for ($serverAttempt=0; $serverAttempt -lt 60; $serverAttempt++) {
    try { $null = Invoke-WebRequest ($baseUrl + '/web/login') -UseBasicParsing -TimeoutSec 3; break }
    catch { if ($serverAttempt -eq 59) { throw }; Start-Sleep -Seconds 1 }
}
$workspace = Split-Path -Parent $PSScriptRoot
$profile = Join-Path $PSScriptRoot 'browser-profile'
if ($LiveReadOnly) { $profile = Join-Path $profile 'live' }
$browser = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$arguments = @('--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', "--remote-debugging-port=$DebugPort", ('--user-data-dir="' + $profile + '"'), '--window-size=1440,1000', 'about:blank')
$process = Start-Process -FilePath $browser -ArgumentList $arguments -WindowStyle Hidden -PassThru
$socket = $null
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try { $pages = Invoke-RestMethod "http://127.0.0.1:$DebugPort/json/list"; $ready = $true; break } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Headless Chrome did not start' }
    $page = @($pages | Where-Object type -eq 'page')[0]
    $socket = New-Object System.Net.WebSockets.ClientWebSocket
    $socket.ConnectAsync([uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
    $script:messageId = 0
    function Invoke-CDP([string]$Method, $Parameters = @{}) {
        $script:messageId++
        $requestId = $script:messageId
        $request = @{ id=$requestId; method=$Method; params=$Parameters } | ConvertTo-Json -Depth 30 -Compress
        $bytes = [Text.Encoding]::UTF8.GetBytes($request)
        $segment = New-Object 'System.ArraySegment[byte]' -ArgumentList (,$bytes)
        $socket.SendAsync($segment,[Net.WebSockets.WebSocketMessageType]::Text,$true,[Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
        while ($true) {
            $stream = New-Object System.IO.MemoryStream
            try {
                do {
                    $buffer = New-Object byte[] 65536
                    $part = New-Object 'System.ArraySegment[byte]' -ArgumentList (,$buffer)
                    $cancel = New-Object Threading.CancellationTokenSource(60000)
                    try { $received = $socket.ReceiveAsync($part,$cancel.Token).GetAwaiter().GetResult() } finally { $cancel.Dispose() }
                    $stream.Write($buffer,0,$received.Count)
                } until ($received.EndOfMessage)
                $message = [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
            } finally { $stream.Dispose() }
            if ($message.id -eq $requestId) {
                if ($message.error) { throw ($message.error | ConvertTo-Json -Compress) }
                return $message.result
            }
        }
    }
    function Invoke-JS([string]$Expression) {
        $reply = Invoke-CDP 'Runtime.evaluate' @{expression=$Expression; awaitPromise=$true; returnByValue=$true}
        if ($reply.exceptionDetails) { throw ($reply.exceptionDetails | ConvertTo-Json -Depth 5 -Compress) }
        return $reply.result.value
    }
    function Open-OdooPage([string]$Path, [string]$Name) {
        Invoke-CDP 'Page.navigate' @{url=($baseUrl + $Path)} | Out-Null
        $success = $false
        $stable = 0
        $previousText = ''
        for ($attempt = 0; $attempt -lt 90; $attempt++) {
            Start-Sleep -Milliseconds 500
            try {
                $status = Invoke-JS "JSON.stringify({ready:!!document.querySelector('.o_action_manager .o_control_panel,.o-mail-Discuss'),error:!!document.querySelector('.o_error_dialog'),text:(document.body?.innerText||'').slice(0,1500)})"
            } catch { continue }
            $state = $status | ConvertFrom-Json
            if ($state.error) { throw "Odoo UI error on ${Name}: $($state.text)" }
            if ($state.ready -and $state.text.Length -gt 30 -and $state.text -eq $previousText -and $state.text -notmatch '\nLoading$') { $stable++ } else { $stable=0 }
            $previousText = $state.text
            if ($stable -ge 2) { $success=$true; break }
        }
        if (-not $success) { throw "Page not ready: $Name; $status" }
        $shot = Invoke-CDP 'Page.captureScreenshot' @{format='png'; captureBeyondViewport=$false}
        [IO.File]::WriteAllBytes((Join-Path $PSScriptRoot "evidence/browser-$artifactPrefix$Name.png"),[Convert]::FromBase64String($shot.data))
        return @{name=$Name; path=$Path; text=$state.text; passed=$true}
    }
    Invoke-CDP 'Page.enable' | Out-Null
    Invoke-CDP 'Page.navigate' @{url=($baseUrl + '/web/login')} | Out-Null
    for ($loginAttempt=0; $loginAttempt -lt 30; $loginAttempt++) {
        Start-Sleep -Milliseconds 500
        $origin = Invoke-JS 'location.origin'
        if ($origin -eq $baseUrl) { break }
        if ($loginAttempt -eq 29) { throw "Login page origin is $origin" }
    }
    $settings = Get-Content (Join-Path $workspace '.env') | ConvertFrom-StringData
    $migration = Get-Content (Join-Path $PSScriptRoot '.env') | ConvertFrom-StringData
    $loginDb = if ($LiveReadOnly) { 'food_distribution' } else { $migration.MIGRATION_DB }
    $payload = @{jsonrpc='2.0'; method='call'; params=@{db=$loginDb; login=$settings.ODOO_LOGIN; password=$settings.ODOO_PASSWORD}; id=1} | ConvertTo-Json -Depth 5 -Compress
    $auth = Invoke-JS "(async()=>{const r=await fetch('/web/session/authenticate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify($payload)});const j=await r.json();if(j.error)throw new Error(j.error.message);return j.result.uid})()"
    if (-not $auth) { throw 'Browser authentication failed' }
    $checks = @()
    $checks += Open-OdooPage '/odoo' 'home'
    # Resolve native action IDs in the browser's authenticated session.
    $actions = Invoke-JS "(async()=>{const refs=['sale.action_quotations_with_onboarding','purchase.purchase_rfq','stock.stock_picking_type_action','mrp.mrp_production_action','food_distribution_quality.action_food_quality_points','quality_control_oca.action_qc_inspection','food_distribution_planning.forecast_action','food_distribution.act_window_x_nutritional_facts'];const result=[];for(const ref of refs){const r=await fetch('/web/action/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',params:{action_id:ref},id:1})});const j=await r.json();if(j.error)throw new Error(ref+': '+j.error.message);result.push({ref,id:j.result.id})}return JSON.stringify(result)})()"
    foreach ($action in ($actions | ConvertFrom-Json)) {
        $name = $action.ref.Split('.')[0]
        $checks += Open-OdooPage "/odoo/action-$($action.id)" $name
    }
    if ($LiveReadOnly) {
        $checks | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $PSScriptRoot 'evidence/browser-live-results.json') -Encoding utf8
        Write-Output "LIVE_BROWSER_READ_ONLY_CHECKS_PASSED=$($checks.Count)"
        return
    }
    # Exercise an actual create/save operation through the rendered form.
    Invoke-JS "document.querySelector('.o_list_button_add').click(); true" | Out-Null
    $fieldReady = $false
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 500
        $fieldReady = Invoke-JS "!!document.querySelector('.o_field_widget[name=x_name] input')"
        if ($fieldReady) { break }
    }
    if (-not $fieldReady) { throw 'Nutrition create form did not open' }
    $testName = 'BROWSER Nutrition ' + (Get-Date -Format 'HHmmss')
    $testNameJson = $testName | ConvertTo-Json -Compress
    Invoke-JS "(()=>{const i=document.querySelector('.o_field_widget[name=x_name] input');i.value=$testNameJson;i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));return true})()" | Out-Null
    Start-Sleep -Milliseconds 500
    Invoke-JS "(()=>{const save=document.querySelector('.o_form_button_save');if(save){save.click()}else{const input=document.querySelector('.o_field_widget[name=x_name] input');input.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',bubbles:true}));document.querySelector('.o_control_panel').click()}return true})()" | Out-Null
    Start-Sleep -Seconds 2
    $saved = Invoke-JS "(async()=>{const j=await(await fetch('/web/dataset/call_kw/x_nutritional_facts/search_count',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',params:{model:'x_nutritional_facts',method:'search_count',args:[[['x_name','=',$testNameJson]]],kwargs:{}},id:1})})).json();if(j.error)throw Error(j.error.message);return j.result})()"
    if ($saved -ne 1) { throw 'Nutrition row was not saved by the browser form' }
    $checks += @{name='nutrition-create-save'; passed=$true; record_name=$testName}
    $meta = Get-Content -Raw (Join-Path $PSScriptRoot 'evidence/migration-validation.json') | ConvertFrom-Json
    $productAction = Invoke-JS "(async()=>{const j=await(await fetch('/web/dataset/call_kw/ir.actions.act_window/search_read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',params:{model:'ir.actions.act_window',method:'search_read',args:[[['res_model','=','product.template']]],kwargs:{fields:['id'],limit:1}},id:1})})).json();if(j.error)throw Error(j.error.message);return j.result[0].id})()"
    $checks += Open-OdooPage "/odoo/action-$productAction/$($meta.preview.product_template_id)" 'product-form'
    $labelTab = Invoke-JS "(()=>{const tab=[...document.querySelectorAll('.o_notebook .nav-link')].find(x=>x.textContent.trim()==='Label');if(!tab)return false;tab.click();return true})()"
    if (-not $labelTab) { throw 'Food Label tab not available on the product form' }
    Start-Sleep -Seconds 1
    $shot = Invoke-CDP 'Page.captureScreenshot' @{format='png'; captureBeyondViewport=$false}
    [IO.File]::WriteAllBytes((Join-Path $PSScriptRoot 'evidence/browser-product-label.png'),[Convert]::FromBase64String($shot.data))
    $labelContent = Invoke-JS "JSON.stringify({note:document.querySelector('.o_field_widget[name=x_label_note] textarea')?.value||document.querySelector('.o_field_widget[name=x_label_note]')?.innerText,ingredients:document.querySelector('.o_field_widget[name=x_ingredient_ids]')?.innerText,nutrition:document.querySelector('.o_field_widget[name=x_nutritional_fact_ids]')?.innerText})"
    $labelContent | Set-Content (Join-Path $PSScriptRoot 'evidence/browser-food-fields.json') -Encoding utf8
    if ($labelContent -notmatch 'MIGRATION PREVIEW Egg' -or $labelContent -notmatch 'Keep refrigerated') { throw 'Food Label tab missing ingredient or label note' }
    $checks += @{name='product-food-fields'; passed=$true; product_id=$meta.preview.product_id}
    $checks | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $PSScriptRoot 'evidence/browser-results.json') -Encoding utf8
    Write-Output "BROWSER_CHECKS_PASSED=$($checks.Count)"
} finally {
    if ($socket) { $socket.Dispose() }
    # Shut down only the browser started with this migration-specific profile.
    if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
}
