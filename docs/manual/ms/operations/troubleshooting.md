# Penyelesaian masalah

- Pembaca: pengendali IT
- Berkaitan: [senarai semak pelaksanaan](deployment-checklist.md), [tugas berjadual](scheduled-jobs.md), [rujukan arahan](commands.md)

| Gejala | Perkara yang perlu disemak |
|---|---|
| Dialihkan ke halaman keselamatan sejurus selepas log masuk | Dasar pengesahan dua faktor ialah "wajib" dan tempoh tangguh telah berlalu. Selesai setelah pengguna mendaftar. Dasar ini terdapat di bawah **Tetapan > Keselamatan** |
| 403 dalam panel pentadbiran | Pengguna tiada penetapan peranan yang sah dengan kebenaran `admin_panel.access` (`Buka panel pentadbiran`). Buka pengguna tersebut di bawah **Pengguna dan akses > Pengguna** dan semak senarai **Penetapan peranan** (tempoh, skop) |
| Item menu tidak kelihatan | Peranan tiada kebenaran untuk skrin itu (contohnya `roles.view`) |
| Kod e-mel tidak diterima | Tetapan e-mel (`MAIL_*`, `DEFAULT_FROM_EMAIL`), entri `Kod e-mel dihantar` di bawah **Audit > Peristiwa keselamatan**, had penghantaran (bagi setiap pengguna sekali seminit, lima kali sejam) |
| Halaman log masuk menjawab `429 Too Many Requests` | Satu alamat melebihi `LOGIN_RATE_LIMIT_PER_IP` (lalai 30) percubaan seminit. Jika ramai pengguna disekat serentak, semak bahawa `TRUSTED_PROXY_COUNT` sepadan dengan bilangan sebenar proksi (semua orang kelihatan sebagai alamat Nginx); di belakang NAT kampus, naikkan nilai tersebut ([senarai semak pelaksanaan](deployment-checklist.md#proksi-dan-alamat-klien)) |
| Log masuk gagal dengan kata laluan yang betul | Log masuk dikunci (`Log masuk dikunci` dalam **peristiwa keselamatan**) atau akaun tidak aktif. Lepaskan kunci dengan `uv run manage.py security_unlock_user <email> --reason="..."` |
| Skrin menunjukkan 0 baris data individu lain | Mungkin normal (keselamatan peringkat baris). Pastikan pelaku sesi pangkalan data ditetapkan dengan melihat lajur pengguna dalam **Audit > Perubahan data** |
| `400 Bad Request` | Nama hos yang diminta tiada dalam `DJANGO_ALLOWED_HOSTS` |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` tiada alamat `https://`, atau Nginx tidak menghantar `X-Forwarded-Proto` |
| Pengalihan HTTPS tanpa henti | Nginx tidak menghantar `X-Forwarded-Proto $scheme`, jadi Django melihat permintaan HTTP (`SECURE_PROXY_SSL_HEADER`) |
| Skrin tanpa gaya atau skrip, ralat `manifest.json` | `npm ci && npm run build` (`static/dist/`), `collectstatic`, lokasi `/static/` Nginx. Pengeluaran menggunakan `VITE_DEV_MODE=false` |
| Sebahagian skrin dipaparkan dalam bahasa Inggeris | `compilemessages --ignore=.venv` tidak dijalankan (tiada fail `.mo`). Bagi rentetan baharu, `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | Aplikasi cuba menjalankan DDL sebagai `app_runtime`. Jalankan migrasi hanya dengan `uv run manage.py migrate` atau `setup_install` (kedua-duanya menggunakan `app_migrator` secara automatik) |
| `Audit records are append-only` | Percubaan untuk mengemas kini atau memadam jadual audit. Sekatan ini memang disengajakan |
| Penjanaan PDF gagal | `uv run manage.py pdf_sample`, status Gotenberg, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Tugas baris gilir tersekat | Semak sambungan pekerja (worker) dan tugas yang gagal dalam Flower, `uv run celery -A config inspect active`, sambungan Redis (`REDIS_URL`) |
| Tugas berjadual tidak berjalan, `/api/v1/health/` menjawab `degraded` | Beat telah berhenti (tiada degupan jantung penjadual selama lebih 5 minit). Semak proses beat dan lognya. Hanya satu beat |
| `Received unregistered task` dalam log pekerja | Pekerja masih menjalankan kod sebelumnya. Mulakan semula pekerja selepas pelaksanaan |
| Penutupan semester tidak selesai | Tugas `grading.close_term_records` yang gagal dalam Flower. Betulkan puncanya, kemudian mulakan semula penutupan semester (pengiraan bagi setiap pelajar memberikan hasil yang sama apabila dijalankan semula) |

Pengesanan bagi setiap permintaan: dengan nilai pengepala respons `X-Request-Id` anda boleh mencari log (`request_id` dalam JSON), log aktiviti, perubahan data dan peristiwa keselamatan sekali gus. Apabila Nginx menghantar `X-Request-Id $request_id`, log akses Nginx turut disertakan. Larian arahan menggunakan ID larian yang bermula dengan `cmd-`.
