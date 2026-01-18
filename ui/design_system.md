# Skyflo Design System

## 1. Color Palette

### Base Colors (Tailwind Config)
These colors are explicitly defined in your `tailwind.config.ts` and extend the default palette.

| Token Name | Hex Value | Usage |
| :--- | :--- | :--- |
| **Dark** | | **Core dark theme backgrounds** |
| `dark.DEFAULT` | `#121214` | Main background |
| `dark.secondary` | `#1c1e24` | Secondary background |
| `dark.navbar` | `#070708` | Navigation bar background |
| `dark.hover` | `#16161a` | Hover states |
| `dark.active` | `#1B1B1C` | Active states |
| `dark.red` | `#f54257` | Error / Destructive actions |
| **Border** | | **Border colors** |
| `border.DEFAULT` | `#1c1c1c` | Default borders |
| `border.focus` | `#545457` | Focus state borders |
| `border.menu` | `#4E4E50` | Menu borders |
| **Button** | | **Button specific colors** |
| `button.primary` | `#0F1D2F` | Primary button background |
| `button.hover` | `#1a6fc9` | Primary button hover |
| **Brand** | | |
| `primary-cyan` | `#30CAF1` | Primary brand accent |

### Semantic Theme Colors (CSS Variables)
These colors use HSL values and adapt based on the theme (Light/Dark).

| Token Variable | Light Mode (HSL) | Dark Mode (HSL) | Description |
| :--- | :--- | :--- | :--- |
| `--background` | `0 0% 100%` (White) | `224 71.4% 4.1%` (Dark Blue-Grey) | Page background |
| `--foreground` | `224 71.4% 4.1%` | `210 20% 98%` (Off-white) | Default text color |
| `--card` | `0 0% 100%` | `224 71.4% 4.1%` | Card background |
| `--popover` | `0 0% 100%` | `224 71.4% 4.1%` | Popover/Modal background |
| `--primary` | `220.9 39.3% 11%` | `210 20% 98%` | Primary action background |
| `--primary-foreground` | `210 20% 98%` | `220.9 39.3% 11%` | Text on primary color |
| `--secondary` | `220 14.3% 95.9%` | `215 27.9% 16.9%` | Secondary action background |
| `--muted` | `220 14.3% 95.9%` | `215 27.9% 16.9%` | Muted background |
| `--accent` | `220 14.3% 95.9%` | `215 27.9% 16.9%` | Accent background |
| `--destructive` | `0 84.2% 60.2%` | `0 62.8% 30.6%` | Destructive action background |
| `--border` | `220 13% 91%` | `215 27.9% 16.9%` | Default border color |
| `--input` | `220 13% 91%` | `215 27.9% 16.9%` | Input field border |
| `--ring` | `224 71.4% 4.1%` | `216 12.2% 83.9%` | Focus ring color |

## 2. Typography

* **Font Family**: `Inter` (Sans-serif)
* **Weights**:
  * Regular (400)
  * Bold (700)
* **Features**: `rlig` (Required Ligatures), `calt` (Contextual Alternates) enabled by default.

## 3. Spacing & Radius

* **Border Radius**:
  * `--radius`: `0.5rem` (8px)
  * `lg`: `var(--radius)` (8px)
  * `md`: `calc(var(--radius) - 2px)` (6px)
  * `sm`: `calc(var(--radius) - 4px)` (4px)

## 4. Effects & Utilities

### Liquid Glass Effect (`.lg-*`)
A custom set of utilities to create a "liquid glass" visual style.
* **Wrapper**: `.lg-wrapper` (Radius: 28px, Overflow: hidden)
* **Effect Layer**: `.lg-effect` (Backdrop blur 10px, SVG distortion filter)
* **Tint**: `.lg-tint` (Dark overlay `rgba(12, 12, 24, 0.25)`)
* **Dim**: `.lg-dim` (Linear gradient top-down)
* **Shine**: `.lg-shine` (Inner shadow for depth)
* **Vignette**: `.lg-vignette` (Radial gradient)

### Animations
* **Dots**: A typing/loading animation (`.dots`) that cycles through `.`, `..`, `...`.
* **Gradient Move**: A background position animation (`.animate-gradient`) for moving gradients (3s duration).

### Scrollbar
Custom styled webkit scrollbar:
* **Width**: 12px
* **Track**: Dark (`#1E1E1E`) with rounded corners.
* **Thumb**: Lighter grey (`#4B4B4B`) with border, darkening on hover.
