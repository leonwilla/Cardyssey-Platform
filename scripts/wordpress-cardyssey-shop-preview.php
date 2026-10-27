<?php
/**
 * Plugin Name: Cardyssey Shop Design Preview
 * Description: Optional cream/orange WooCommerce storefront preview. Original design stays the default.
 * Version: 0.1.0
 *
 * Deploy as wp-content/mu-plugins/cardyssey-shop-design-preview.php.
 * Enable on shop.cardyssey.de with ?design=preview; revert with ?design=classic.
 */
if (!defined('ABSPATH')) { exit; }

function cardyssey_preview_enabled() {
    if (is_admin() || (function_exists('wp_doing_ajax') && wp_doing_ajax())) return false;
    return isset($_COOKIE['cardyssey_shop_design']) && $_COOKIE['cardyssey_shop_design'] === 'preview';
}
add_action('init', function () {
    if (is_admin() || !isset($_GET['design'])) return;
    $requested = sanitize_text_field(wp_unslash($_GET['design']));
    if ($requested !== 'preview' && $requested !== 'classic') return;
    $value = $requested === 'preview' ? 'preview' : '';
    setcookie('cardyssey_shop_design', $value, [
        'expires' => $value ? time() + 86400 * 30 : time() - 3600,
        'path' => '/',
        'secure' => is_ssl(),
        'httponly' => true,
        'samesite' => 'Lax'
    ]);
    $_COOKIE['cardyssey_shop_design'] = $value;
}, 1);

add_filter('body_class', function ($classes) {
    if (cardyssey_preview_enabled()) $classes[] = 'cardyssey-shop-preview';
    return $classes;
});
add_action('wp_head', function () {
    if (!cardyssey_preview_enabled()) return;
    ?>
    <style id="cardyssey-shop-preview-css">
    body.cardyssey-shop-preview {
      --cdy-paper:#f5efe5;--cdy-panel:#fffaf3;--cdy-ink:#1e2c26;
      --cdy-secondary:#57675d;--cdy-orange:#e6512d;--cdy-border:#dfd0be;
      background:var(--cdy-paper)!important;color:var(--cdy-ink)!important;
      color-scheme:light;
    }
    body.cardyssey-shop-preview :is(#page,.site,.site-content,.content-area,main,article,.woocommerce,.wp-site-blocks) {
      color:var(--cdy-ink);
    }
    body.cardyssey-shop-preview :is(header,footer,.site-header,.site-footer,.wp-block-template-part) {
      background:var(--cdy-panel);color:var(--cdy-ink);
      border-color:var(--cdy-border);
    }
    body.cardyssey-shop-preview :is(.woocommerce ul.products li.product,.wp-block-post,.wc-block-grid__product,.woocommerce div.product) {
      background:var(--cdy-panel);color:var(--cdy-ink);
      border:1px solid var(--cdy-border);border-radius:18px;
      padding:14px;overflow:hidden;
    }
    body.cardyssey-shop-preview :is(h1,h2,h3,h4,.woocommerce-loop-product__title,.wc-block-grid__product-title) {
      color:var(--cdy-ink);
    }
    body.cardyssey-shop-preview :is(p,.woocommerce-product-details__short-description) {color:var(--cdy-secondary)}
    body.cardyssey-shop-preview :is(.price,.woocommerce-Price-amount) {color:#b94122;font-weight:700}
    body.cardyssey-shop-preview :is(.button,.wp-element-button,button[type=submit],input[type=submit],.wc-block-components-button) {
      background:var(--cdy-orange);color:#fffaf3;border-radius:12px;border:0;
    }
    body.cardyssey-shop-preview :is(input:not([type=checkbox]),textarea,select) {
      background:#fffdf9;color:var(--cdy-ink);border:1px solid var(--cdy-border);border-radius:10px;
    }
    body.cardyssey-shop-preview a {text-underline-offset:3px}
    body.cardyssey-shop-preview :is(a,button,input,select,textarea):focus-visible {
      outline:3px solid var(--cdy-orange);outline-offset:3px;
    }
    @media(prefers-reduced-motion:reduce){body.cardyssey-shop-preview * {scroll-behavior:auto!important}}
    </style>
    <?php
}, 50);

add_action('wp_footer', function () {
    if (!cardyssey_preview_enabled()) return;
    $classic = add_query_arg('design', 'classic', home_url('/'));
    echo '<div style="position:fixed;right:16px;bottom:16px;z-index:9999;background:#fffaf3;border:1px solid #dfd0be;border-radius:100px;padding:10px 16px;box-shadow:0 8px 30px #0002;font:600 13px system-ui;color:#1e2c26">Cardyssey Testdesign · <a style="color:#ad3f24" href="' . esc_url($classic) . '">Altes Design</a></div>';
}, 50);
