# FlowAlchemy — Architecture Review (Round 3)

> **Hasil review oleh Claude** (acting as Senior Full-Stack Architect / CTO advisor)
> Direview terhadap: `Implementation Plan & Review Document` — UI/UX Batch 1-10, Credential Injection System, E2E 26/26
> Tanggal review: 19 September 2026
> Review sebelumnya: `FlowAlchemy-Review.md` (Round 1) dan `FlowAlchemy-Review-Round2.md` (Round 2)

---

## Ringkasan Umum

Dokumentasi round ini jauh lebih rapi dari Round 2 — semua angka file count (8 new, 17 modified, 3 test files, 4 backend modified, 3 backend unchanged) **cocok** dengan tabel detailnya masing-masing. Tidak ada kontradiksi internal seperti yang saya temukan sebelumnya soal migration count/Postgres setup. Ini poin plus konkret untuk kedisiplinan dokumentasi.

Fitur credential injection (`{{cred:ID}}` placeholder) juga desain yang bagus dari sisi UX — user tidak pernah menempel raw secret langsung ke field config, tapi lewat picker yang insert placeholder. Sayangnya, ada satu masalah arsitektural yang cukup serius di balik desain UX yang bagus ini, yang saya bahas sebagai temuan #2 di bawah.

---

## 🔴 Critical — Baru Ditemukan

### 1. `_credentials_store` In-Memory: Bukan Cuma "Data Hilang Saat Restart" — Ini Kemungkinan Broken di Topologi Sekarang

Kamu sudah menandai ini sebagai Critical, tapi menurut saya deskripsinya kurang menangkap tingkat keparahannya. Dari arsitektur yang kamu dokumentasikan sendiri:

```
FastAPI Backend (Port 8000)  ← proses A
    ↓
Redis Queue
    ↓
Worker Process → WorkflowEngine → Executors  ← proses B (terpisah)
```

`get_credential_value(cred_id, user_id)` dipanggil dari `worker.py` (proses B), tapi kalau `_credentials_store` adalah dict Python biasa yang hidup di memori proses FastAPI (proses A), maka **proses Worker secara struktural tidak punya akses ke dict itu sama sekali** — ini bukan cuma soal "hilang pas restart", tapi kemungkinan credential resolution **tidak bekerja sama sekali** begitu API server dan Worker berjalan sebagai proses terpisah (yang menurut arsitektur ini, memang seharusnya begitu).

Kalau di testing lokal ini "kelihatan jalan", kemungkinan besar karena API dan Worker kebetulan masih dijalankan dalam satu proses Python yang sama saat development — begitu dipisah jadi 2 proses (atau di-scale ke >1 worker), fitur ini akan gagal diam-diam.

**Rekomendasi:** pindahkan `_credentials_store` ke tabel database (`credentials` table, belum ada di schema yang saya lihat sejauh ini) — ini sekaligus menyelesaikan masalah data-loss-on-restart yang sudah kamu tandai.

### 2. Kemungkinan Kebocoran Nilai Credential ke Execution History (Plaintext di DB)

Ini temuan baru yang menurut saya lebih penting dari soal salt di bawah. Dari flow yang kamu dokumentasikan sendiri di Appendix:

```
6. Resolution walks config recursively
   → Replaces "{{cred:3}}" with get_credential_value(3, user_id)
7. Executor receives clean config
   → HttpRequestExecutor: headers = {"Authorization": "Bearer sk-abc123..."}
```

Config yang **sudah di-resolve** (berisi secret asli, plaintext) inilah yang diteruskan ke executor. Pertanyaannya: apakah `node_executions.input_data` (kolom JSON yang menyimpan input tiap node untuk keperluan Execution History UI) menyimpan config **sebelum** atau **sesudah** resolusi? Kalau yang tersimpan adalah versi sesudah resolusi (yang tampaknya begitu, karena `ExecutionHistory.tsx` perlu menampilkan apa yang benar-benar dikirim), berarti:

- Setiap kali workflow yang pakai credential dijalankan, **secret asli dalam bentuk plaintext ikut tersimpan permanen di database**, di luar sistem enkripsi yang sudah susah payah kamu bangun.
- User (atau siapapun yang bisa lihat execution history — termasuk lewat screenshot demo portofolio!) bisa melihat token/API key asli lewat tab History, bukan cuma placeholder `{{cred:ID}}`.

Ini secara efektif membuat seluruh sistem enkripsi credential (AES-256/Fernet) **percuma** untuk tujuan "protect secret at rest", karena ada jalur lain (execution log) yang menyimpannya polos.

**Rekomendasi:** sebelum data node input/output di-persist ke `node_executions`, jalankan proses **redaction** — ganti balik nilai yang berasal dari credential dengan placeholder atau masked string (`sk-***abc1`) sebelum disimpan ke DB atau dikirim ke frontend. Nilai plaintext hasil resolusi hanya boleh hidup sesaat di memori, tepat di titik panggilan HTTP-nya saja — tidak boleh menyentuh lapisan persistence sama sekali.

### 3. Encryption Salt Belum Persisten (Sudah Kamu Tandai — Tambahan Rekomendasi)

Kamu sudah benar menandai ini Critical. Tambahan dari saya: solusi "derive dari `SECRET_KEY`" itu bisa jalan, tapi ada opsi yang lebih sederhana dan lebih sedikit poin kegagalan — **skip password-based key derivation sepenuhnya**. Generate satu Fernet key sekali (`Fernet.generate_key()`), simpan sebagai env var terpisah (`CREDENTIAL_ENCRYPTION_KEY`), dan pakai langsung tanpa derivation. Ini menghilangkan kebutuhan salt sama sekali — Fernet sudah menangani IV/nonce secara internal per pesan.

---

## 🟡 Moderate — Perkuat Temuanmu Sendiri

- **Duplicate credential picker pattern** (`HeadersEditor`, `BodyEditor`, `NodeConfigForm`) — setuju ini worth di-refactor. Karena polanya identik (dropdown + insert placeholder di posisi cursor), ini kandidat bagus untuk custom hook (`useCredentialPicker`) yang mengembalikan handler + dropdown state, dipakai di ketiga komponen — lebih clean daripada extract jadi komponen UI penuh kalau layout tiap tempat sedikit beda.
- **Silent error swallowing** (`api.get('/credentials').catch(() => {})`) — setuju, minimal `console.error` atau toast diam-diam, karena kalau fetch credentials gagal, user akan bingung kenapa credential picker-nya kosong tanpa ada indikasi error sama sekali.
- **Rate limiting / execution quota masih belum ada** (carry-over dari Round 2) — sekarang risikonya sedikit naik karena node executor bisa membawa credential asli (API key pihak ketiga). Eksekusi paralel tak terbatas + credential injection berarti user (sengaja atau tidak) bisa memicu rate-limit/ban dari API pihak ketiga atas nama akun mereka sendiri dalam skala besar. Masih oke ditunda ke item async runtime, tapi prioritasnya naik sedikit dengan adanya fitur ini.

---

## ⚪ Minor — Setuju dengan Penilaianmu

- `TransformParamsEditor` useEffect deps `[operation]` saja — oke untuk sekarang, cukup kasih komentar di kode kenapa deps-nya sengaja dibatasi supaya reviewer lain (atau kamu 6 bulan lagi) tidak "memperbaiki" jadi infinite loop.
- `CREDENTIAL_PATTERN.search(str(config))` — setuju minor, ukuran config node biasanya kecil, tidak worth dioptimasi sekarang.
- E2E test numbering & fragile CSS selector — setuju, tidak blocking, bisa dirapikan kapan saja.

---

## ✅ Yang Dikerjakan dengan Baik

- **Dokumentasi round ini konsisten secara internal** — semua angka file count cocok dengan tabel detail. Peningkatan nyata dari Round 2.
- **WebSocket reconnection dengan exponential backoff + polling fallback** — pattern yang tepat untuk real-time UI yang tidak boleh macet total kalau koneksi putus.
- **Theme FOUC prevention via inline script di `index.html`** — teknik standar yang benar, banyak developer skip ini dan hasilnya flash tema salah sebelum React mount.
- **Pemisahan concern executor vs credential resolution** — `http_request.py`, `transform.py`, `condition.py` tidak berubah sama sekali karena mereka cukup menerima config yang sudah bersih dari engine. Ini desain yang benar — executor tidak perlu tahu soal credential sama sekali, jadi kalau nanti mekanisme credential berubah, executor tidak perlu disentuh.
- **Modal dengan focus trap + ARIA + Escape + scroll lock** — detail aksesibilitas yang sering dilewatkan solo dev, tapi kamu sudah tangani dengan benar.

---

## Prioritas Tindakan

1. **Selesaikan dulu temuan #1 dan #2** (credential store lintas-proses + kebocoran plaintext ke execution history) sebelum fitur credential ini dipakai untuk demo portofolio — dua-duanya berpotensi membuat fitur "secure credential management" yang kamu banggakan justru jadi bukti sebaliknya kalau ada yang cek execution history-nya langsung.
2. Setelah itu, pindahkan `_credentials_store` ke tabel DB — ini menyelesaikan temuan #1 dan known issue "data hilang saat restart" sekaligus.
3. Refactor salt/key derivation sesuai rekomendasi #3.
4. Baru lanjut ke item lain (refactor credential picker, rate limiting) sesuai prioritas moderate.

---

*Review ini adalah lanjutan dari `FlowAlchemy-Review.md` (Round 1) dan `FlowAlchemy-Review-Round2.md` (Round 2), berdasarkan dokumen implementasi yang dibagikan pada 19 September 2026.*
