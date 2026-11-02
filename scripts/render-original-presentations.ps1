param([Parameter(Mandatory=$true)][string]$Sources)
$ErrorActionPreference = 'Stop'
$items = Get-Content -LiteralPath $Sources -Raw -Encoding UTF8 | ConvertFrom-Json
$pending = @($items | Where-Object {$_.originalPresentation -and !(Test-Path -LiteralPath $_.originalPresentation.pdfCache)})
if (!$pending.Count) { Write-Output 'Original presentation PDFs are cached.'; exit 0 }
$powerpoint = New-Object -ComObject PowerPoint.Application
try {
    $powerpoint.AutomationSecurity = 3
    $powerpoint.DisplayAlerts = 1
    foreach ($item in $pending) {
        $deck = $item.originalPresentation
        $cacheDirectory = Split-Path -Parent $deck.pdfCache
        New-Item -ItemType Directory -Force -Path $cacheDirectory | Out-Null
        $presentation = $null
        try {
            # Read-only, no presentation window; macros disabled above.
            $presentation = $powerpoint.Presentations.Open($deck.source, -1, 0, 0)
            $presentation.SaveAs($deck.pdfCache, 32)
            Write-Output "$($item.lessonId): $($presentation.Slides.Count) original slides"
        } finally {
            if ($presentation) { $presentation.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
        }
    }
} finally {
    $powerpoint.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint)
}
