# Tugas berjadual dan baris gilir

- Pembaca: pengendali IT
- Berkaitan: [senarai semak pelaksanaan](deployment-checklist.md), [integriti audit](audit-and-maintenance.md), [rujukan arahan](commands.md)

## Proses yang berjalan berterusan

| Proses | Arahan | Semakan |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Pekerja baris gilir | `uv run celery -A config worker --loglevel=INFO` | **Workers** dalam Flower, `uv run celery -A config inspect ping` |
| Penjadual | `uv run celery -A config beat --loglevel=INFO` (**tepat satu proses secara keseluruhan**) | `scheduler` dalam `/api/v1/health/`, log beat |
| Pemantau baris gilir (pilihan) | `uv run celery -A config flower --port=5555` | Hanya pada rangkaian dalaman atau di belakang sekatan akses Nginx |

Ketiga-tiganya menggunakan kod dan pemboleh ubah persekitaran yang sama. Contoh systemd:

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

Cipta satu lagi perkhidmatan dengan bentuk yang sama untuk beat dengan `ExecStart=... celery -A config beat --loglevel=INFO`. Walaupun dengan beberapa pelayan, dayakan perkhidmatan beat pada satu pelayan sahaja.

## Tugas berjadual

Pendaftarannya ialah `beat_schedule` dalam `config/celery.py`; beat menyelaraskan penjadual pangkalan data django-celery-beat (jadual `django_celery_beat_*`) dengannya apabila ia bermula. Masa adalah dalam zon waktu pelayan (`APP_TIMEZONE`, UTC secara lalai). Setiap tugas berjadual memegang kunci Redis (`single_instance`), jadi tugas yang sama tidak pernah berjalan dua kali pada masa yang sama.

| Tugas (nama Celery) | Kekerapan | Arahan yang melakukan perkara sama | Pengesanan kegagalan |
|---|---|---|---|
| `admission.expire_drafts` | Setiap hari pada 03:10 | `admission_expire_drafts` | Menjalankan arahan itu sendiri, jadi setiap larian direkodkan dalam log aktiviti (log `command`). Jika tiada rekod lebih daripada sehari, semak beat dan pekerja |
| `registration.release_reserved_seats` | Setiap 5 minit | `registration_release_reserved_seats` | Tiada rekod audit. Jika peruntukan tempat duduk yang masa pelepasannya telah berlalu masih mempunyai `release_processed_at` yang kosong, semak beat |
| `registration.promote_waitlists` | Setiap jam, tepat pada jamnya | `waitlist_promote` | Tiada entri log aktiviti (pendaftaran yang dinaikkan muncul dalam perubahan data sebagai `system:task:registration.promote_waitlists`). Hasil tugas dalam Flower (seksyen, kenaikan) |
| `lms.reconcile` | Setiap hari pada 02:30 | `lms_reconcile` | Rekod penyegerakan bagi setiap pautan (panel pentadbiran **Integrasi LMS**), hasil tugas dalam Flower |
| `audit.seal` | Setiap hari pada 03:30 | `audit_seal` | Memeterai rantaian hash audit ([integriti audit](audit-and-maintenance.md)). Semak jika `audit_verify_chain` menunjukkan lebih banyak baris yang belum dimeterai daripada jumlah bagi sehari |
| `core.heartbeat` | Setiap minit | Tiada | Menulis masa larian terakhir ke kunci cache `system:heartbeat`. `/api/v1/health/` menjawab `degraded` apabila ia berusia lebih daripada 5 minit |

## Tugas baris gilir

| Tugas (nama Celery) | Dicetuskan oleh | Catatan |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Satu tugas bagi setiap kelompok rekod (group). Jika sesuatu kelompok gagal, jalankan arahan sekali lagi (rekod yang sudah menggunakan kunci semasa dilangkau) |
| `registration.promote_waitlist` | Gugur atau tarik diri daripada pendaftaran, pelepasan peruntukan tempat duduk | Hanya satu berjalan bagi setiap seksyen (kunci Redis, pendua dihalang). Kenaikan senarai menunggu menyemak semula setiap peraturan pendaftaran. Dimasukkan ke baris gilir selepas transaksi dilakukan (commit) |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, tutup semester dalam panel pentadbiran | Satu chord: tugas bagi 100 pelajar, kemudian tugas penyudah (kedudukan Senarai Dekan, perubahan status semester, memaklumkan kakitangan yang memulakannya). Kemajuan ialah baris `job_batches` `term-close:{term code}`, dipaparkan dalam panel pentadbiran. Tugas kelompok mencuba semula sehingga 3 kali apabila berlaku ralat pangkalan data; jika masih gagal, seluruh kelompok ditandakan gagal dan tugas penyudah tidak berjalan. Betulkan puncanya, kemudian mulakan semula penutupan semester (pengiraan bagi setiap pelajar memberikan hasil yang sama apabila dijalankan semula) |
| `importing.import_chunk` | Import CSV dalam panel pentadbiran, `reference_import` | Satu tugas bagi setiap ketulan (chunk). Hasil dalam `imports`, baris yang gagal dalam `failed_import_rows` (hasil import dalam panel pentadbiran) |
| `lms.sync_section`, `lms.sync_enrollment` | Peristiwa perubahan seksyen dan pendaftaran | Apabila gagal, dicuba semula sehingga 3 kali dengan selang seminit. `lms.reconcile` setiap malam membetulkan yang selebihnya |

Semasa tugas berjalan, pelaku pangkalan data direkodkan sebagai `system:task:{task name}` (contohnya `system:task:grading.close_term_records`), bersama ID permintaan dan pengguna bagi permintaan yang memasukkannya ke baris gilir.

Flower memaparkan tugas yang gagal (**Tasks**, keadaan `FAILURE`) dan pengecualiannya (exception). Tugas Celery menggunakan `acks_late`, jadi tugas yang terganggu oleh pekerja yang mati akan berjalan semula. Setiap tugas dibina untuk memberikan hasil yang sama apabila dijalankan semula (idempoten).
