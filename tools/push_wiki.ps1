# Публикация страниц docs/ в GitHub Wiki.
#
# Вики-репозиторий создаётся на GitHub только после того, как в веб-интерфейсе
# нажата кнопка «Create the first page». Пока этого не сделано, git clone
# возвращает «Repository not found» — скрипт в этом случае подсказывает шаг.
#
# Запуск:  powershell -ExecutionPolicy Bypass -File tools\push_wiki.ps1
#
# Соответствие «файл в docs/ -> страница вики» лежит в tools/wiki_pages.json и
# читается с явной кодировкой UTF-8. Это существенно: Windows PowerShell 5.1
# читает .ps1 без BOM в системной ANSI-кодировке, и кириллица, записанная прямо
# в скрипте, превратилась бы в мусор в именах страниц. Имена страниц формируются
# только из JSON, поэтому скрипт можно сохранять в любой кодировке.

param(
    # Однократная уборка: удалить страницы вики, которых нет в wiki_pages.json.
    # Нужна после переименования страниц — старые файлы остаются в репозитории вики.
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$owner    = "1997yyyy"
$repo     = "Human-Machine-Interface-Design-LAB4"
$wikiUrl  = "git@github.com:$owner/$repo.wiki.git"
$webUrl   = "https://github.com/$owner/$repo"
$rawBase  = "https://raw.githubusercontent.com/$owner/$repo/main"

$root     = Split-Path -Parent $PSScriptRoot
$docs     = Join-Path $root "docs"
$mapPath  = Join-Path $PSScriptRoot "wiki_pages.json"
$tmp      = Join-Path $env:TEMP "lab4-wiki"

$utf8 = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path $mapPath)) {
    Write-Host "Не найден $mapPath" -ForegroundColor Red
    exit 1
}
$manifest = ConvertFrom-Json ([System.IO.File]::ReadAllText($mapPath, [System.Text.Encoding]::UTF8))

# --- клонирование или обновление локальной копии вики -----------------------
if (Test-Path (Join-Path $tmp ".git")) {
    Push-Location $tmp
    git pull --ff-only 2>&1 | Out-Null
    $pullCode = $LASTEXITCODE
    Pop-Location
    if ($pullCode -ne 0) {
        Remove-Item -Recurse -Force $tmp
        git clone $wikiUrl $tmp
    }
} else {
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    git clone $wikiUrl $tmp
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Вики ещё не создана. Откройте" -ForegroundColor Yellow
        Write-Host "  $webUrl/wiki" -ForegroundColor Yellow
        Write-Host "и нажмите «Create the first page», сохраните любую строку." -ForegroundColor Yellow
        Write-Host "После этого запустите скрипт снова." -ForegroundColor Yellow
        exit 1
    }
}

# --- перекрёстные ссылки: docs/02-requirements.md -> имя страницы вики ------
$linkMap = @{}
foreach ($p in $manifest.pages) {
    $linkMap[$p.src] = [System.IO.Path]::GetFileNameWithoutExtension($p.file)
}

foreach ($p in $manifest.pages) {
    $srcPath = Join-Path $docs $p.src
    if (-not (Test-Path $srcPath)) {
        Write-Host ("нет файла: docs/{0}" -f $p.src) -ForegroundColor Red
        exit 1
    }
    $text = [System.IO.File]::ReadAllText($srcPath, [System.Text.Encoding]::UTF8)

    # Картинки лежат в репозитории; вики их не копирует, поэтому ссылка
    # заменяется на raw-адрес ветки main.
    $text = $text -replace '\]\(\.\./assets/', "]($rawBase/assets/"

    foreach ($src in $linkMap.Keys) {
        $text = $text -replace [regex]::Escape("]($src)"), "]($($linkMap[$src]))"
    }

    [System.IO.File]::WriteAllText((Join-Path $tmp $p.file), $text, $utf8)
    Write-Host ("страница: {0,-38} <- docs/{1}" -f $p.file, $p.src)
}

# --- удаление страниц, которые скрипт создавал раньше, но больше не нужны ---
$statePath = Join-Path $tmp ".managed-pages"
$now = @($manifest.pages | ForEach-Object { $_.file })

if ($Clean) {
    $keep = @($now) + @("_Sidebar.md")
    foreach ($f in Get-ChildItem -Path $tmp -Filter "*.md") {
        if ($keep -notcontains $f.Name) {
            Remove-Item $f.FullName
            Write-Host ("удалена посторонняя страница: {0}" -f $f.Name) -ForegroundColor Yellow
        }
    }
}
if (Test-Path $statePath) {
    $prev = @([System.IO.File]::ReadAllLines($statePath, [System.Text.Encoding]::UTF8) | Where-Object { $_.Trim() -ne "" })
    foreach ($old in $prev) {
        if (($now -notcontains $old) -and (Test-Path (Join-Path $tmp $old))) {
            Remove-Item (Join-Path $tmp $old)
            Write-Host ("удалена устаревшая страница: {0}" -f $old) -ForegroundColor Yellow
        }
    }
}
[System.IO.File]::WriteAllLines($statePath, $now, $utf8)

# --- боковое меню -----------------------------------------------------------
$sb = New-Object System.Collections.Generic.List[string]
$sb.Add("### " + $manifest.sidebar_title)
$sb.Add("")
foreach ($p in $manifest.pages) {
    $slug = [System.IO.Path]::GetFileNameWithoutExtension($p.file)
    $sb.Add("- [" + $p.title + "](" + $slug + ")")
}
[System.IO.File]::WriteAllText((Join-Path $tmp "_Sidebar.md"), ($sb -join "`n") + "`n", $utf8)

# --- коммит и отправка ------------------------------------------------------
$msgPath = Join-Path $env:TEMP "lab4-wiki-msg.txt"
[System.IO.File]::WriteAllText($msgPath, $manifest.commit_message, $utf8)

Push-Location $tmp
git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
    Pop-Location
    Write-Host "Изменений нет: вики уже соответствует docs/." -ForegroundColor Green
    exit 0
}
git -c user.name="Zeng Yaoxin" -c user.email="yaoxinzeng@gmail.com" commit -q -F $msgPath
git push origin HEAD
$code = $LASTEXITCODE
Pop-Location

if ($code -eq 0) {
    Write-Host ""
    Write-Host "Готово: $webUrl/wiki" -ForegroundColor Green
} else {
    Write-Host "Не удалось отправить страницы (код $code)." -ForegroundColor Red
    exit $code
}
