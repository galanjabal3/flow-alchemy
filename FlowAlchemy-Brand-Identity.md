# FlowAlchemy — Brand Identity Guide

> Disusun untuk mendukung positioning "visual workflow automation, developer-grade" dengan sentuhan mistis-teknis yang membedakan dari builder automation generik (Zapier, n8n, dsb).

---

## 1. Color Palette

### Palette A — "Molten Circuit"
*Tema: alkimia klasik (emas cair) bertemu dark-mode developer tool.*

| Role | Hex | Preview |
|---|---|---|
| Primary | `#7C3AED` (violet electric) | Warna utama brand — CTA, active node, link |
| Secondary | `#22D3EE` (cyan flow) | Elemen "flow" — connector line, progress state |
| Accent | `#F59E0B` (molten gold) | Highlight sukses/premium — sangat kena tema "alchemy" |
| Background | `#0B0E14` (near-black navy) | Base canvas, kontras tinggi tanpa pure black |
| Surface | `#161B26` (charcoal navy) | Card, sidebar, node panel |

**Kenapa cocok:** Violet + cyan menangkap sisi "flow" (cair, bergerak, energik) sementara gold accent secara literal mewakili "alchemy" — emas adalah tujuan akhir alkimia klasik. Kombinasi ini juga sudah terbukti familiar di kalangan developer tool modern (Linear, Raycast pakai pendekatan serupa), jadi terasa profesional bukan norak.

---

### Palette B — "Deep Current"
*Tema: lebih tenang, mengutamakan "flow" sebagai gerakan air, alchemy sebagai aksen sekunder.*

| Role | Hex | Preview |
|---|---|---|
| Primary | `#0EA5E9` (sky current) | Warna utama — tombol, node aktif |
| Secondary | `#6366F1` (indigo transmute) | Transisi/gradient partner untuk primary |
| Accent | `#D946EF` (arcane magenta) | Highlight khusus — error state atau fitur premium |
| Background | `#0A0F1C` (deep ocean navy) | Base canvas |
| Surface | `#131A2B` (slate navy) | Card, panel |

**Kenapa cocok:** Palette ini lebih "calm technical" — cocok kalau kamu mau kesan tool serius/enterprise-ready, bukan playful. Gradient biru→indigo→magenta juga natural dipakai di garis koneksi antar node (menyimbolkan data "mengalir" dan "bertransformasi" sepanjang path), yang jadi salah satu visual signature paling kuat untuk produk workflow builder.

---

### Palette C — "Arcane Terminal"
*Tema: nostalgia terminal/hacker hijau-amber, dipadukan aksen ungu magis.*

| Role | Hex | Preview |
|---|---|---|
| Primary | `#10B981` (terminal emerald) | Warna utama — familiar buat developer (mengingatkan terminal/matrix) |
| Secondary | `#F59E0B` (amber signal) | Warning/secondary state |
| Accent | `#A855F7` (mystic violet) | Elemen "alchemy" — dipakai sangat sparingly untuk fitur spesial |
| Background | `#08090C` (true near-black) | Base canvas paling gelap dari 3 opsi |
| Surface | `#14161B` (graphite) | Card, panel |

**Kenapa cocok:** Paling "developer-coded" dari ketiganya — hijau terminal langsung terasa familiar dan trustworthy buat audiens teknis, sementara violet accent dipakai terbatas supaya elemen "magic"-nya terasa spesial, bukan dominan. Risikonya: hijau-di-atas-hitam sudah agak umum dipakai tool developer lain, jadi diferensiasinya lebih tipis dibanding Palette A atau B.

**Rekomendasi saya: Palette A ("Molten Circuit")** — paling seimbang antara diferensiasi visual dan literal-nya konsep "flow + alchemy", dan gold accent memberi satu warna "signature" yang gampang diingat di screenshot portfolio.

---

## 2. Logo Concept

### Konsep 1 — "Flask Flow"
**Deskripsi visual:** Bentuk labu alkimia (erlenmeyer flask) yang disederhanakan jadi bentuk geometris minimal, dengan cairan di dalamnya digambarkan sebagai garis alir (flow line) yang keluar dari mulut flask membentuk kurva menuju sebuah node/titik.
**Elemen:** Flask outline (alchemy) + curved flow line + node dot di ujung (workflow).
**Variasi warna:** Outline flask pakai Secondary (cyan), cairan/flow line pakai gradient Primary→Accent (violet→gold) untuk kesan "transformasi" berlangsung di dalam alur.

### Konsep 2 — "Infinity Transmute"
**Deskripsi visual:** Simbol infinity (∞) yang digambar ulang sebagai dua loop tidak simetris — satu sisi lebih "cair/organik" (mewakili flow), sisi lainnya lebih "geometris/bersudut" (mewakili logic/code). Titik pertemuan di tengah diberi gradient sebagai simbol transmutasi.
**Elemen:** Bentuk infinity asimetris + gradient transisi di titik tengah.
**Variasi warna:** Sisi organik pakai gradient Primary→Secondary, sisi geometris pakai warna solid Accent — kontras ini menegaskan "dua dunia" (visual builder vs executable code) yang disatukan produk ini.

### Konsep 3 — "Hex Node"
**Deskripsi visual:** Hexagon (bentuk klasik simbol alkimia/molekul) berisi 3 node kecil yang terhubung garis membentuk pola alir sederhana di dalamnya — dari satu sudut hexagon ke sudut lain, menyerupai huruf "F" secara implisit.
**Elemen:** Hexagon outline + 3 connected nodes + implicit "F" negative space.
**Variasi warna:** Hexagon outline monokrom (bisa putih/abu untuk versi dark, hitam untuk versi light), node dan garis alir pakai warna Primary — desain ini paling fleksibel untuk versi 1-warna (favicon kecil, watermark, dsb).

**Rekomendasi saya: Konsep 3 ("Hex Node")** — paling robust untuk skala kecil (favicon 16x16 tetap terbaca karena bentuknya geometris tegas), dan hexagon-nya punya makna ganda yang kuat (alkimia + struktur molekul/graph data) tanpa perlu ilustrasi rumit.

---

## 3. Typography

| Peran | Font | Alasan |
|---|---|---|
| **Heading (display)** | **Space Grotesk** | Geometris, sedikit futuristik, punya karakter tanpa terasa "generic tech". Tersedia gratis di Google Fonts, readable di ukuran besar untuk hero text/section title. |
| **Body (sans-serif)** | **Inter** | Standar de-facto untuk produk developer modern (dipakai GitHub, Linear, Vercel) — sangat readable di ukuran kecil, mendukung banyak weight, dan netral sehingga tidak bentrok dengan heading yang lebih ekspresif. |
| **Code/monospace** | **JetBrains Mono** | Dirancang khusus untuk kode, ligature bagus, karakter mudah dibedakan (0 vs O, 1 vs l) — penting untuk platform yang menampilkan JSON config atau generated code. |

Alternatif kalau ingin variasi: **Sora** (pengganti Space Grotesk, sedikit lebih soft) atau **Fira Code** (pengganti JetBrains Mono kalau mau ligature yang lebih playful).

---

## 4. Tagline

1. **"Where Logic Becomes Liquid"**
2. **"Automate Anything. Visually. Instantly."**
3. **"Transmute Complexity Into Clarity"**
4. **"Workflows That Flow, Not Fight"**
5. **"Code-Free Power, Developer-Grade Depth"**

**Rekomendasi saya:** #1 atau #3 — keduanya paling literal menangkap "flow" + "alchemy" sekaligus, dan cukup abstrak untuk terasa premium tanpa over-promise fitur spesifik yang mungkin belum semua ada di MVP.

---

## 5. UI Style

| Aspek | Rekomendasi | Catatan |
|---|---|---|
| **Border radius** | **Rounded, moderate (8-12px)** | Cukup lembut untuk terasa modern/approachable, tapi tidak se-playful pill-shape yang biasanya dipakai produk consumer. Node card di canvas bisa sedikit lebih besar radius (12-16px) untuk membedakan dari UI chrome di sekitarnya. |
| **Shadow style** | **Subtle + glow accent** | Shadow biasa yang tipis untuk depth dasar, ditambah *glow effect* halus (box-shadow warna Primary/Accent dengan opacity rendah) di elemen aktif — misal node yang sedang running atau node yang di-hover. Ini elemen kecil yang langsung memperkuat kesan "magic/alchemy" tanpa harus berlebihan. |
| **Gradient usage** | **Moderate, purposeful** | Jangan gradient di semua tempat — pakai spesifik di: (1) garis koneksi antar node saat data mengalir, (2) tombol CTA utama, (3) logo/brand mark. Di luar itu, tetap solid color supaya UI tetap tenang untuk kerja teknis yang butuh fokus lama. |
| **Animation style** | **Subtle-to-moderate, dengan satu "signature motion"** | Sebagian besar transisi UI (modal, tab, hover) tetap subtle dan cepat (150-200ms) supaya tidak mengganggu produktivitas. Tapi alokasikan satu animasi signature yang lebih ekspresif: partikel/dot kecil yang "mengalir" di sepanjang garis koneksi saat workflow sedang eksekusi — ini elemen visual yang paling mungkin bikin recruiter berhenti scroll pas lihat demo, sekaligus paling relevan secara fungsional (menunjukkan data flow secara real-time).

---

## Ringkasan Rekomendasi Final

| Kategori | Pilihan |
|---|---|
| Color Palette | **Molten Circuit** (violet + cyan + gold) |
| Logo | **Hex Node** (hexagon + connected nodes) |
| Heading Font | Space Grotesk |
| Body Font | Inter |
| Code Font | JetBrains Mono |
| Tagline | "Where Logic Becomes Liquid" |
| Border Radius | 8-12px |
| Shadow | Subtle + glow accent pada elemen aktif |
| Gradient | Moderate, dipakai di connection line, CTA, dan logo saja |
| Animation | Subtle base + signature "flowing particle" di connection line saat eksekusi |
