#!/usr/bin/env python3
"""Tüm skill'leri (.claude/skills/*) gömülü olarak içeren kurulum dosyalarını ve zip'leri üretir.

Çalıştır:  python3 kurulum/olustur.py
"""
import pathlib, zipfile

kok = pathlib.Path(__file__).resolve().parent.parent
skills_dir = kok / ".claude" / "skills"
kurulum = kok / "kurulum"
skills = sorted(p.name for p in skills_dir.iterdir() if (p / "SKILL.md").is_file())

TURKCE_BLOK = """<!-- turkce-baslangic -->
# Dil
Kullanıcıyla her zaman Türkçe konuş (kullanıcı İngilizce anlamıyor). Açıklamaları, özetleri ve soruları Türkçe yaz; kod, komut ve dosya adlarını olduğu gibi bırak.
<!-- turkce-bitis -->"""

def oku(ad):
    return (skills_dir / ad / "SKILL.md").read_text(encoding="utf-8").rstrip("\n")

# ---- Mac / Linux ----
sh = ["#!/usr/bin/env bash",
      "# Tüm skill'leri bu bilgisayara kurar: ~/.claude/skills/<ad>/SKILL.md",
      "set -euo pipefail",
      'kok="$HOME/.claude"',
      'mkdir -p "$kok/skills"', ""]
for ad in skills:
    sh += [f'mkdir -p "$kok/skills/{ad}"',
           f"cat > \"$kok/skills/{ad}/SKILL.md\" <<'SKILL_EOF'", oku(ad), "SKILL_EOF",
           f'echo "Kuruldu: {ad}"', ""]
sh += ['touch "$kok/CLAUDE.md"',
       "if ! grep -q 'turkce-baslangic' \"$kok/CLAUDE.md\"; then",
       "cat >> \"$kok/CLAUDE.md\" <<'CLAUDE_EOF'", "", TURKCE_BLOK, "CLAUDE_EOF",
       '  echo "Türkçe konuşma ayarı eklendi: $kok/CLAUDE.md"', "fi",
       f'echo ""', f'echo "Toplam {len(skills)} skill kuruldu. Claude Code\'u yeniden açınca hazır olacak."']
(kurulum / "kur-mac-linux.sh").write_text("\n".join(sh) + "\n", encoding="utf-8")
(kurulum / "kur-mac-linux.sh").chmod(0o755)

# ---- Windows ----
ps = ["# Tüm skill'leri bu bilgisayara kurar: %USERPROFILE%\\.claude\\skills\\<ad>\\SKILL.md",
      "$kok = Join-Path $env:USERPROFILE '.claude'",
      "$utf8 = New-Object System.Text.UTF8Encoding $false",
      "function Kur($ad, $icerik) {",
      "  $hedef = Join-Path $kok \"skills\\$ad\"",
      "  New-Item -ItemType Directory -Force -Path $hedef | Out-Null",
      "  [System.IO.File]::WriteAllText((Join-Path $hedef 'SKILL.md'), $icerik + \"`n\", $utf8)",
      "  Write-Host \"Kuruldu: $ad\"",
      "}", ""]
for ad in skills:
    ps += [f"Kur '{ad}' @'", oku(ad), "'@", ""]
ps += ["$claudeMd = Join-Path $kok 'CLAUDE.md'",
       "if (-not (Test-Path $claudeMd)) { [System.IO.File]::WriteAllText($claudeMd, '', $utf8) }",
       "if (-not (Select-String -Path $claudeMd -Pattern 'turkce-baslangic' -Quiet)) {",
       "  $blok = @'", "", TURKCE_BLOK, "'@",
       "  [System.IO.File]::AppendAllText($claudeMd, $blok + \"`n\", $utf8)",
       "  Write-Host \"Turkce konusma ayari eklendi: $claudeMd\"", "}",
       "Write-Host ''",
       f"Write-Host 'Toplam {len(skills)} skill kuruldu. Claude Code''u yeniden acinca hazir olacak.'"]
# PowerShell 5 BOM'suz UTF-8'i yanlış okur; BOM ile yaz.
(kurulum / "kur-windows.ps1").write_text("\n".join(ps) + "\n", encoding="utf-8-sig")

# ---- Zip'ler ----
zdir = kok / "skill-zipleri"
zdir.mkdir(exist_ok=True)
for eski in zdir.glob("*.zip"):
    eski.unlink()
for ad in skills:
    with zipfile.ZipFile(zdir / f"{ad}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(skills_dir / ad / "SKILL.md", f"{ad}/SKILL.md")
with zipfile.ZipFile(kok / "kurulum.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in ["kur-windows.bat", "kur-windows.ps1", "kur-mac-linux.sh"]:
        z.write(kurulum / f, f)
print(f"{len(skills)} skill: {', '.join(skills)}")
