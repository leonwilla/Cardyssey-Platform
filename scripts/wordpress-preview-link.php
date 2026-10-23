<?php
/** Plugin Name: Cardyssey Shop Design Comparison Link */
add_action('wp_footer', function () {
    if (is_admin()) return;
    echo '<a href="https://cardyssey.de/preview-shop" class="cardyssey-design-preview-link" aria-label="Neues Shop-Design als Vorschau ansehen">✦ Neues Shop-Design ansehen ↗</a>';
    echo '<style>.cardyssey-design-preview-link{position:fixed;bottom:20px;right:20px;z-index:99990;display:inline-flex;align-items:center;gap:8px;padding:12px 18px;border-radius:999px;background:#e6512d;color:#fff!important;font:600 14px/1.2 system-ui,sans-serif;text-decoration:none!important;box-shadow:0 8px 24px rgba(0,0,0,.22)}.cardyssey-design-preview-link:hover{background:#b9381e;color:#fff!important}@media(max-width:600px){.cardyssey-design-preview-link{bottom:14px;right:14px;padding:11px 14px;font-size:13px}}</style>';
}, 100);
