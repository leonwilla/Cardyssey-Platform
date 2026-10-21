<?php
/**
 * Plugin Name: Cardyssey Private Shop Gate
 * Description: Only Cardyssey accounts approved by the private-access service may view the shop.
 */
add_action('init', function () {
    if (defined('WP_CLI') && WP_CLI) return;
    if (defined('DOING_CRON') && DOING_CRON) return;
    $access = isset($_COOKIE['cardyssey_access']) ? (string) $_COOKIE['cardyssey_access'] : '';
    $refresh = isset($_COOKIE['cardyssey_refresh']) ? (string) $_COOKIE['cardyssey_refresh'] : '';
    $headers = array('Accept' => 'application/json');
    if ($access !== '' || $refresh !== '') {
        $cookies = array();
        if ($access !== '') $cookies[] = 'cardyssey_access=' . rawurlencode($access);
        if ($refresh !== '') $cookies[] = 'cardyssey_refresh=' . rawurlencode($refresh);
        $headers['Cookie'] = implode('; ', $cookies);
    }
    $response = wp_remote_get('https://cardyssey.de/api/internal/private-access', array(
        'timeout' => 8, 'redirection' => 0, 'headers' => $headers,
    ));
    if (!is_wp_error($response) && wp_remote_retrieve_response_code($response) === 204) {
        header('Cache-Control: private, no-store');
        return;
    }
    if ((defined('REST_REQUEST') && REST_REQUEST) || wp_doing_ajax() || $_SERVER['REQUEST_METHOD'] !== 'GET') {
        status_header(403);
        header('Cache-Control: no-store');
        exit('Private shop access required.');
    }
    wp_redirect('https://cardyssey.de/login', 302);
    exit;
}, 1);
