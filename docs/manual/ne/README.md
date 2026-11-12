# विद्यार्थी सूचना प्रणाली प्रयोगकर्ता पुस्तिका (नेपाली)

दैनिक रूपमा प्रणाली सञ्चालन गर्ने कर्मचारी तथा प्रणाली स्थापना, डिप्लोय र मर्मतसम्भार गर्ने IT सञ्चालकहरूका लागि। स्क्रिनहरू नेपालीमा उपलब्ध छन् (भाषा मेनु)।

अन्य भाषाहरू: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md)। कोरियाली संस्करण मूल स्रोत हो; अन्य संस्करणहरू मातृभाषी समीक्षाको प्रतीक्षामा रहेका अनुवाद हुन्।

## प्रशासक पुस्तिका

[admin/README.md](admin/README.md) — अध्याय 1 देखि 28 सम्म: सुरुवात, प्रयोगकर्ता र भूमिकादेखि संस्थाको सेटअप, भर्ना, विषय दर्ता, ग्रेड, प्रमाणपत्र, स्नातक र LMS एकीकरणसम्म।

## सञ्चालन

| फाइल | विषयवस्तु |
|---|---|
| [installation.md](operations/installation.md) | आवश्यकताहरू, डेटाबेस भूमिकाहरू, वातावरण कन्फिगरेसन, पहिलो स्थापना र अद्यावधिक |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python र gunicorn सेटिङ, उत्पादन वातावरण चरहरू, डिप्लोय प्रक्रिया, नियमित जाँच |
| [commands.md](operations/commands.md) | सबै व्यवस्थापन कमान्ड (`uv run manage.py ...`) को सन्दर्भ: विकल्पहरू, अडिट अभिलेख, निकास कोड, उदाहरणहरू |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | लामो समय चल्ने प्रक्रियाहरू (Celery worker, beat), निर्धारित कार्यहरू र क्यु कार्यहरू, विफलता कसरी पत्ता लगाउने (Flower) |
| [backup-restore.md](operations/backup-restore.md) | के ब्याकअप गर्ने, डम्प र पुनर्स्थापनाका उदाहरणहरू, पुनर्स्थापना अभ्यास |
| [security-keys.md](operations/security-keys.md) | तीन गोप्य कुञ्जीहरू, तिनलाई कसरी भण्डारण गर्ने, व्यक्तिगत विवरण कुञ्जी परिवर्तन |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | अडिट ह्यास चेन, अवधारण र छँटाइ, फाइल सफाइ, स्वास्थ्य जाँच |
| [load-testing.md](operations/load-testing.md) | विषय दर्ताको उच्च चापका लागि लोड परीक्षण (Locust) र worker सङ्ख्या सम्बन्धी निर्णय |
| [troubleshooting.md](operations/troubleshooting.md) | सामान्य लक्षणहरू, के जाँच गर्ने, प्रति-अनुरोध ट्रेसिङ |

## अन्य कागजातहरू

- [LMS एकीकरण गाइड](../../lms-integration-guide.md): API र LMS कनेक्टरहरू (विकासकर्ताहरूका लागि)
- [भाषा थप्ने](../../development/adding-a-language.md), [नामकरण नियमहरू](../../development/naming.md), [समीक्षा जाँचसूची](../../development/review-checklist.md) (विकासकर्ताहरूका लागि)
- [कागजात सूची](../../README.md)
