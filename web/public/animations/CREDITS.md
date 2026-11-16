# Animation and logo

- **Source animation:** `animation.lottie`, provided by the user.
- Default animation ID: `ai-animation-flow-1`.
- `scripts/prepare_animation.py` extracts its JSON unchanged into `animation.json` for `lottie-web`. The original archive is preserved and remains the source of truth.
- Renderer: `lottie-web` (MIT), https://github.com/airbnb/lottie-web
- Motion is paused when `prefers-reduced-motion: reduce` is enabled.
- The earlier purple orb from LottieFiles is no longer used.

**Logo and favicon:** user-provided `public/images/logo.png`, used without recoloring.
