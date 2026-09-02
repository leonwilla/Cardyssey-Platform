<?php

if (!defined('ABSPATH')) {
    exit;
}

function cardyssey_setup() {
    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('woocommerce');

    register_nav_menus([
        'primary' => __('Hauptnavigation', 'cardyssey'),
    ]);
}
add_action('after_setup_theme', 'cardyssey_setup');

function cardyssey_assets() {
    wp_enqueue_style(
        'cardyssey-style',
        get_stylesheet_uri(),
        [],
        wp_get_theme()->get('Version')
    );
}
add_action('wp_enqueue_scripts', 'cardyssey_assets');

function cardyssey_shop_url() {
    if (function_exists('wc_get_page_id')) {
        $shop_id = wc_get_page_id('shop');

        if ($shop_id > 0) {
            return get_permalink($shop_id);
        }
    }

    return home_url('/shop/');
}
