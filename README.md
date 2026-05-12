# News Card Tool (Ở Đây Có Tin Tức Style)

Tool tự động tổng hợp tin tức, render ảnh card kiểu Ở Đây Có Tin Tức News, và **đăng tự động lên Facebook Page mỗi sáng 7h** — tất cả miễn phí qua GitHub Actions.

## Tính năng

- 📰 Lấy tin từ RSS feeds Việt Nam (VnExpress, Tuổi Trẻ, Dân Trí)
- 🤖 Tóm tắt nội dung bằng Claude API
- 🎨 Render ảnh card 1200x1600 theo layout Ở Đây Có Tin Tức
- 📤 Đăng tự động lên Facebook Page (single hoặc album)
- ⏰ Schedule mỗi sáng 7h Vietnam time qua GitHub Actions
- 💰 **Chi phí: 0đ** (chỉ tốn Claude API nếu dùng — ~$0.001/card)

## Kiến trúc

```
┌─────────────────┐
│ GitHub Actions  │  cron "0 0 * * *"  (00:00 UTC = 7:00 VN)
│   ubuntu-latest │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  run_daily.py                           │
│  ┌──────────┐  ┌───────────┐  ┌──────┐  │
│  │ RSS feed │→ │ Summarize │→ │Render│  │
│  └──────────┘  │  (Claude) │  │ card │  │
│                └───────────┘  └──┬───┘  │
│                                  │      │
│                                  ▼      │
│                          ┌──────────┐   │
│                          │ Facebook │   │
│                          │  Page    │   │
│                          └──────────┘   │
└─────────────────────────────────────────┘
```

## Setup

### 1. Fork/clone repo này lên GitHub

```bash
git clone <your-repo>
cd news-card-tool
```

### 2. Tạo Facebook App + lấy Page Access Token

**Bước 2.1:** Vào [developers.facebook.com](https://developers.facebook.com) → Create App → chọn **Business** type.

**Bước 2.2:** Add product **Facebook Login** + cài permission:
- `pages_manage_posts`
- `pages_read_engagement`

**Bước 2.3:** Vào [Graph API Explorer](https://developers.facebook.com/tools/explorer/), chọn app, click "Get User Access Token" với các permissions trên, copy token (short-lived ~1h).
- token: EAAcC4flFRIEBRZALmZCMiKo2EQpGsNe2okA58XGqtcXiyTqF9LeX15Tiz9E5cslUoaveclRoiFWWLFhLPG5OdbxRpKLy6giJYVLcTd2HxkWCDZAYXQrJdkcgUR8R8e01SluDBmvMRiQ9Uc4AgFOPukhaC4yEIZBJNPWiZCRHNiREhZBtq45jdpuq6HOHV2IMRhdpVmDhNv6aqTWpE01JmiZC1jYbal5tI7v5uvTl06oeCn5ECrwvhzgKrCQZBR2fVaWMIMc0Tu1U6W99vraQRRaldWwo0OMJx1yJZAARFQ58ZD

**Bước 2.4:** Đổi sang long-lived Page Token (never expires):

```bash
python scripts/get_page_token.py \
    --app-id YOUR_APP_ID \
    --app-secret YOUR_APP_SECRET \
    --user-token SHORT_LIVED_TOKEN_FROM_STEP_2.3
```

Script in ra `FB_PAGE_ID` và `FB_PAGE_ACCESS_TOKEN` (never expires).

> ⚠️ Lưu ý: để app đăng được bài public, cần qua **App Review** của Facebook (chỉ approve permission `pages_manage_posts`, mất 1-3 ngày). Trong lúc chờ, app vẫn đăng được lên Page của chính bạn ở mode Development.

### 3. Lấy Anthropic API key (tùy chọn, để tóm tắt AI)

[console.anthropic.com](https://console.anthropic.com) → API Keys → Create. Nếu không có, tool fallback cắt summary RSS.

### 4. Add secrets vào GitHub repo

GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Required | Value |
|---|---|---|
| `FB_PAGE_ID` | ✅ | ID từ step 2.4 |
| `FB_PAGE_ACCESS_TOKEN` | ✅ | Page token never-expire |
| `ANTHROPIC_API_KEY` | tùy chọn | `sk-ant-...` |

### 5. Enable Actions

Tab **Actions** trong repo → Enable workflows → workflow "Daily News Post" sẽ chạy tự động 7h sáng mỗi ngày.

Test ngay bằng **workflow_dispatch**: Actions → Daily News Post → Run workflow → bật "Dry run" để xem ảnh artifact mà chưa đăng FB.

## Chi phí

| Thành phần | Giá |
|---|---|
| GitHub Actions (public repo) | Free unlimited |
| GitHub Actions (private repo) | 2000 phút/tháng free, mỗi run ~3 phút → ~666 runs/tháng dư dả |
| Facebook Graph API | Free |
| Claude API (Haiku 4.5) | ~$0.001/card, 4 cards/ngày × 30 = **~$0.12/tháng** |
| RSS feeds | Free |

**Tổng: $0–$0.15/tháng** tùy có dùng AI summarize hay không.

## Sử dụng local

### Test render 1 card
```bash
python main.py --manual \
    --title "Tiêu đề" --summary "Mô tả..." \
    --image https://... --source "vnexpress.net"
```

### Test full pipeline (dry-run, không đăng FB)
```bash
DRY_RUN=1 python run_daily.py
```

### Chạy thật (đăng FB)
```bash
export FB_PAGE_ID=...
export FB_PAGE_ACCESS_TOKEN=...
export ANTHROPIC_API_KEY=...
python run_daily.py
```

## Tinh chỉnh

**Đổi giờ chạy:** sửa cron trong `.github/workflows/daily-news.yml`. Lưu ý cron của GH Actions dùng **UTC**:
- 7h sáng VN = 0h UTC → `"0 0 * * *"`
- 6h sáng VN = 23h UTC (hôm trước) → `"0 23 * * *"`

**Đổi feeds:** sửa `FEEDS_TO_USE` và `MAX_CARDS` trong `run_daily.py`. Thêm feed mới trong `news_fetcher.py`.

**Đổi layout ảnh:** các constant đầu `card_generator.py` (`CARD_W`, `IMG_H`, `YELLOW`, font sizes...).

**Đổi caption template:** sửa `build_caption()` trong `run_daily.py`.

## Hạn chế cần biết

1. **GitHub Actions cron delay**: thường <5 phút, đỉnh điểm có thể delay tới 15-20 phút. Nếu cần đúng tuyệt đối, deploy lên AWS Lambda + EventBridge (vẫn free tier 1M invocations/tháng).
2. **Facebook chỉ đăng Page**: không đăng được lên profile cá nhân hay Group qua API. Personal posting đã bị Meta chặn từ 2018.
3. **App Review**: nếu Page có nhiều admin và muốn để app public, cần Business Verification + App Review của Meta.
4. **Rate limit**: Page API có giới hạn ~4800 × engaged_users calls/24h. Với 1 bài/ngày, không bao giờ gần limit.

## Cấu trúc files

```
news-card-tool/
├── card_generator.py        # Render ảnh
├── news_fetcher.py          # RSS + scraping
├── summarizer.py            # Claude API
├── publisher/
│   ├── __init__.py
│   └── facebook.py          # Đăng FB Page
├── scripts/
│   └── get_page_token.py    # Helper lấy long-lived token
├── run_daily.py             # Pipeline tổng
├── main.py                  # CLI local
├── requirements.txt
├── fonts/                   # Be Vietnam Pro
├── samples/                 # Ảnh mẫu output
└── .github/
    └── workflows/
        └── daily-news.yml   # GH Actions cron
```
