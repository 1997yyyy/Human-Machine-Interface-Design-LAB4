# Публикация страниц docs/ в GitHub Wiki.
#
# Вики-репозиторий создаётся на GitHub только после того, как в веб-интерфейсе
# нажата кнопка «Create the first page». Пока этого не сделано, git clone
# возвращает «Repository not found» — скрипт в этом случае подсказывает шаг.
#
# Запуск:  powershell -ExecutionPolicy Bypass -File tools\push_wiki.ps1

$ErrorActionPreference = "Stop"

$owner = "1997yyyy"
$repo  = "Human-Machine-Interface-Design-LAB4"
$wikiUrl = "git@github.com:$owner/$repo.wiki.git"
$root = Split-Path -Parent $PSScriptRoot
$docs = Join-Path $root "docs"
$tmp  = Join-Path $env:TEMP "lab4-wiki"
$rawBase = "https://raw.githubusercontent.com/$owner/$repo/main"

# Соответствие: файл в docs/ -> имя страницы вики.
# Имена латиницей там, где это термин, и кириллицей там, где это заголовок:
# GitHub сам приводит пробелы к дефисам в URL страницы.
$pages = [ordered]@{
    "01-home.md"         = "Home.md"
    "02-requirements.md" = "Функциональные-требования.md"
    "03-files.md"        = "Диаграмма-файлов.md"
    "04-spec.md"         = "Дополнительная-спецификация.md"
    "05-database.md"     = "Схема-базы-данных.md"
    "06-api.md"          = "API-проекта.md"
}

# Перекрёстные ссылки внутри docs/ указывают на .md-файлы; в вики страницы
# адресуются по имени, поэтому ссылки переписываются на имена страниц.
$linkMap = @{
    "01-home.md"         = "Home"
    "02-requirements.md" = "Функциональные-требования"
    "03-files.md"        = "Диаграмма-файлов"
    "04-spec.md"         = "Дополнительная-спецификация"
    "05-database.md"     = "Схема-базы-данных"
    "06-api.md"          = "API-проекта"
}

if (Test-Path $tmp) {
    Push-Location $tmp
    git pull --ff-only 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Remove-Item -Recurse -Force $tmp
        git clone $wikiUrl $tmp
    } else {
        Pop-Location
    }
} else {
    git clone $wikiUrl $tmp
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Вики ещё не создана. Откройте" -ForegroundColor Yellow
        Write-Host "  https://github.com/$owner/$repo/wiki" -ForegroundColor Yellow
        Write-Host "и нажмите «Create the first page», сохраните любую строку." -ForegroundColor Yellow
        Write-Host "После этого запустите скрипт снова." -ForegroundColor Yellow
        exit 1
    }
}

foreach ($src in $pages.Keys) {
    $text = [System.IO.File]::ReadAllText((Join-Path $docs $src), [System.Text.Encoding]::UTF8)

    # Картинки лежат в репозитории; вики их не копирует, поэтому ссылка
    # заменяется на raw-адрес ветки main.
    $text = $text -replace '\]\(\.\./assets/', "]($rawBase/assets/"

    foreach ($target in $linkMap.Keys) {
        $text = $text -replace [regex]::Escape("]($target)"), "]($($linkMap[$target]))"
    }

    $out = Join-Path $tmp $pages[$src]
    [System.IO.File]::WriteAllText($out, $text, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host ("страница: {0,-36} <- docs/{1}" -f $pages[$src], $src)
}

# Боковое меню вики: порядок совпадает с порядком страниц.
$sb = New-Object System.Collections.Generic.List[string]
$sb.Add("### Campus Events — ЛР № 4")
$sb.Add("")
foreach ($src in $pages.Keys) {
    $title = $linkMap[$src]
    $slug  = $pages[$src] -replace '\.md$', ''
    $sb.Add("- [$title]($slug)")
}
[System.IO.File]::WriteAllText((Join-Path $tmp "_Sidebar.md"), ($sb -join "`n") + "`n",
    (New-Object System.Text.UTF8Encoding($false)))

Push-Location $tmp
git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
    Pop-Location
    Write-Host "Изменений нет: вики уже соответствует docs/." -ForegroundColor Green
    exit 0
}
git -c user.name="Zeng Yaoxin" -c user.email="yaoxinzeng@gmail.com" commit -q -m "Страницы вики из docs/: требования, файлы, спецификация, база данных, API"
git push origin HEAD
$code = $LASTEXITCODE
Pop-Location

if ($code -eq 0) {
    Write-Host ""
    Write-Host "Готово: https://github.com/$owner/$repo/wiki" -ForegroundColor Green
} else {
    Write-Host "Не удалось отправить страницы (код $code)." -ForegroundColor Red
    exit $code
}
