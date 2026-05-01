# AMS SUPER APP - Development Blueprint & Guidelines

## 🎨 DESIGN PHILOSOPHY: Neobrutalism 2.0
The application follows a "Mission Control" aesthetic characterized by high contrast, bold borders, and vibrant colors.

### 1. Visual Standards
- **Borders**: All primary containers (cards, modals, inputs) MUST have a `3px` solid black border.
- **Shadows**: Hard shadows only. Use `6px 6px 0px 0px #000000` (Light) or `#ffffff` (Dark).
- **Radius**: Large, friendly curves using `30px` for cards and `15-20px` for inputs/buttons.
- **Typography**: Primary font is 'Outfit'. Use `900` weight for headers and `600` for body text.

### 2. Color Palette (CSS Variables)
| Variable | Light Mode | Dark Mode | Usage |
| :--- | :--- | :--- | :--- |
| `--bg` | `#a388ee` (Purple) | `#2d1b5e` | Main Page Background |
| `--main` | `#e3f0af` (Lime) | `#9edb54` | Primary Buttons/Cards |
| `--accent` | `#f9a8d4` (Pink) | `#f472b6` | Secondary Highlights |
| `--white` | `#ffffff` | `#1e1e1e` | Card Backgrounds |
| `--black` | `#000000` | `#ffffff` | Text & Shadows |

### 3. Motion & Animation
- **Floating**: Stat cards use a `4s` floating animation to create a "living" interface.
- **Modals**: Must use the `modalPop` scale animation for a premium "pop-in" effect.
- **Hovers**: Interactive elements should scale slightly (`1.03`) and translate (`-6px, -6px`) with an increased shadow depth.

---

## 🛠️ TECHNICAL ARCHITECTURE

### 1. Modal Implementation (CRITICAL)
**DO NOT** pass full JSON objects through HTML attributes (e.g., `onclick="openEdit({...})"`). This causes character escaping crashes.
- **Pattern**: Use **ID-based Lookup**.
- **Execution**: 
  1. Pass only the record ID to `openEdit(id)`.
  2. The function searches the global `allItems` JavaScript array (injected via Jinja2) for the matching record.
  3. Populate the modal fields from the found object.

### 2. Database Schema (Achievement Model)
- **Primary Keys**: `id` (Integer), `no_urut` (String).
- **Calculation Logic**: 
  - `jumlah_jiwa = jumlah_kk * 5`
  - `jumlah_bjp_jiwa = jumlah_bjp_kk * 5`
- **Technical Fields**: Includes capacity metrics for Mata Air, Tanah, and others, as well as institutional data (POKMAS, Perdes).

### 3. Routing Map
- `/`: **Landing Hub** (`landing.html`)
- `/spm`: **SIMSPAM Dashboard** (`index.html`)
- `/rab`: **RAB Analyzer** (`rab.html`)
- `/remi`: **Remi Counter** (`remi_list.html`)
- `/login`: **Login Portal** (`login.html`)

---

## 📝 DEVELOPMENT NOTES
- **State Management**: The dashboard uses a global `allItems` object as the single source of truth for frontend operations.
- **Theme Support**: Adaptive theme logic is handled via `data-theme="dark"` attribute on the `<body>` tag.
- **SEO & Identity**: App is branded as **AMS SUPER APP** (Air Minum & Sanitasi).

> [!IMPORTANT]
> Always verify database migrations before deploying new fields. The `Achievements` table requires manual column additions or a full DB reset if new technical fields are added.
