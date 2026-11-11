#!/usr/bin/env python3
"""Uzun bir videodan dikey (9:16) kısa videolar (Shorts / Reels / TikTok) çıkarır.

Kullanım:
    python3 shorts.py video.mp4                 # çıktılar: ./shorts_cikti/
    python3 shorts.py video.mp4 -o klasor --min 20 --max 59 --title "Kanal Adı"
    python3 shorts.py video.mp4 --srt altyazi.srt   # altyazıyı videoya göm

Ne yapar:
  1. Sessizlikleri bulur ve videoyu cümle aralarından keser (söz ortasında kesmez).
  2. Her parçayı --min ile --max saniye arasında tutar.
  3. Parçaları ses enerjisine ve sahne değişimine göre puanlar (en heyecanlı olanlar başta).
  4. Her parçayı 1080x1920 dikey yapar: ortada asıl görüntü, arkada bulanık arka plan,
     ses seviyesini eşitler, başa/sona kısa geçiş efekti, isteğe bağlı başlık ve altyazı ekler.
Gerekenler: ffmpeg ve ffprobe (PATH içinde).
"""
import argparse
import json
import os
import re
import subprocess
import sys

FONT = next((f for f in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
] if os.path.exists(f)), None)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "json", path]).stdout
    return float(json.loads(out)["format"]["duration"])


def has_audio(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "a",
               "-show_entries", "stream=index", "-of", "csv=p=0", path]).stdout
    return bool(out.strip())


def silence_midpoints(path, noise_db, min_sil):
    """Sessiz aralıkların orta noktaları = doğal kesim yerleri."""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn",
         "-af", f"silencedetect=noise={noise_db}dB:d={min_sil}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return [(s + e) / 2 for s, e in zip(starts, ends)]


def loudness_per_sec(path):
    """Saniye başına anlık ses yüksekliği (LUFS)."""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn",
         "-af", "ebur128=metadata=1,ametadata=print:key=lavfi.r128.M:file=-",
         "-f", "null", "-"], capture_output=True, text=True)
    vals = {}
    t = None
    for line in err.stdout.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = int(float(m.group(1)))
            continue
        m = re.search(r"lavfi.r128.M=(-?[\d.inf]+)", line)
        if m and t is not None:
            try:
                v = float(m.group(1))
            except ValueError:
                continue
            if v > -70:
                vals.setdefault(t, []).append(v)
    return {k: sum(v) / len(v) for k, v in vals.items()}


def scene_times(path, thresh):
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an",
         "-vf", f"scale=320:-2,select='gt(scene,{thresh})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", err)]


def make_segments(total, cuts, mn, mx):
    """Kesim noktalarını kullanarak mn..mx saniyelik parçalar oluşturur."""
    cuts = sorted(c for c in cuts if 0 < c < total)
    segs, start = [], 0.0
    while total - start >= mn:
        window = [c for c in cuts if start + mn <= c <= start + mx]
        if window:
            end = max(window)                 # mümkün olan en uzun doğal kesim
        else:
            end = min(start + mx, total)      # doğal kesim yoksa sert kes
        segs.append((start, end))
        start = end
    return segs


def score(seg, loud, scenes):
    s, e = seg
    secs = [loud[t] for t in range(int(s), int(e)) if t in loud]
    energy = (sum(secs) / len(secs)) if secs else -70
    peak = max(secs) if secs else -70
    cuts = sum(1 for t in scenes if s <= t < e) / max(e - s, 1) * 60  # dakikadaki sahne
    return energy + 0.5 * (peak - energy) + 0.3 * min(cuts, 30)


def esc_text(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019").replace("%", "\\%")


def render(src, seg, out, title, srt, audio):
    s, e = seg
    d = e - s
    fade = min(0.4, d / 4)
    v = ("[0:v]split=2[a][b];"
         "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
         "boxblur=30:5,eq=brightness=-0.15[bg];"
         "[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
         "[bg][fg]overlay=(W-w)/2:(H-h)/2")
    if title and FONT:
        v += (f",drawtext=fontfile='{FONT}':text='{esc_text(title)}':fontsize=64:"
              "fontcolor=white:borderw=5:bordercolor=black:x=(w-tw)/2:y=180")
    if srt:
        # altyazı zamanlarını parçanın başına kaydırmak için setpts kullan
        sp = srt.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        v += (f",setpts=PTS+{s}/TB,subtitles='{sp}':force_style="
              "'Fontsize=14,Bold=1,Outline=3,Alignment=2,MarginV=60',setpts=PTS-STARTPTS")
    v += f",fade=t=in:st=0:d={fade},fade=t=out:st={d - fade:.3f}:d={fade},format=yuv420p[v]"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-ss", f"{s:.3f}", "-t", f"{d:.3f}", "-i", src,
           "-filter_complex", v, "-map", "[v]"]
    if audio:
        cmd += ["-map", "0:a:0", "-af",
                f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d={fade},"
                f"afade=t=out:st={d - fade:.3f}:d={fade}",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
            "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)


def fmt(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def main():
    p = argparse.ArgumentParser(description="Uzun videodan dikey kısa videolar çıkarır.")
    p.add_argument("video")
    p.add_argument("-o", "--out", default="shorts_cikti")
    p.add_argument("--min", type=float, default=20, help="en kısa parça (sn)")
    p.add_argument("--max", type=float, default=59, help="en uzun parça (sn)")
    p.add_argument("--top", type=int, default=0, help="sadece en iyi N parçayı üret (0 = hepsi)")
    p.add_argument("--title", default="", help="her videonun üstüne yazılacak başlık")
    p.add_argument("--srt", default="", help="tüm videonun .srt altyazısı (isteğe bağlı)")
    p.add_argument("--noise", type=float, default=-35, help="sessizlik eşiği (dB)")
    p.add_argument("--silence", type=float, default=0.35, help="en kısa sessizlik (sn)")
    a = p.parse_args()

    if a.min >= a.max:
        sys.exit("--min, --max'tan küçük olmalı")
    os.makedirs(a.out, exist_ok=True)
    total = duration(a.video)
    audio = has_audio(a.video)
    print(f"Video süresi: {fmt(total)}  |  ses: {'var' if audio else 'yok'}")

    print("Sahne değişimleri aranıyor...")
    scenes = scene_times(a.video, 0.3)
    cuts, loud = list(scenes), {}
    if audio:
        print("Sessizlikler ve ses enerjisi analiz ediliyor...")
        cuts = silence_midpoints(a.video, a.noise, a.silence) or cuts
        loud = loudness_per_sec(a.video)

    segs = make_segments(total, cuts, a.min, a.max)
    if not segs:
        sys.exit(f"Video --min ({a.min} sn) değerinden kısa.")
    ranked = sorted(segs, key=lambda sg: score(sg, loud, scenes), reverse=True)
    if a.top:
        ranked = ranked[:a.top]
    print(f"{len(ranked)} kısa video üretilecek.\n")

    report = []
    for i, sg in enumerate(ranked, 1):
        name = f"short_{i:02d}_{fmt(sg[0]).replace(':', 'm')}s.mp4"
        out = os.path.join(a.out, name)
        print(f"[{i}/{len(ranked)}] {fmt(sg[0])} - {fmt(sg[1])}  ({sg[1] - sg[0]:.1f} sn) -> {name}")
        render(a.video, sg, out, a.title, a.srt, audio)
        report.append({"sira": i, "dosya": name, "baslangic": round(sg[0], 2),
                       "bitis": round(sg[1], 2), "sure": round(sg[1] - sg[0], 2),
                       "puan": round(score(sg, loud, scenes), 2)})
    with open(os.path.join(a.out, "liste.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nBitti. Videolar: {os.path.abspath(a.out)}  (en iyi aday: short_01)")


if __name__ == "__main__":
    main()
