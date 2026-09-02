<!doctype html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <?php wp_head(); ?>
</head>

<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<header class="site-header">
    <div class="container header-inner">

        <a class="brand" href="<?php echo esc_url(home_url('/')); ?>">
            <span class="brand-mark">
                <span class="brand-card"></span>
                <span class="brand-card"></span>
                <span class="brand-orbit"></span>
            </span>

            <span>CARDYSSEY</span>
        </a>

        <nav class="main-nav">
            <a href="<?php echo esc_url(cardyssey_shop_url()); ?>">Shop</a>
            <a href="#tcg-worlds">Trading Cards</a>
            <a href="#collectibles">Collectibles</a>
            <a href="#fashion">Fashion</a>
            <a href="#app">App</a>
        </nav>

        <div class="header-actions">
            <?php if (function_exists('wc_get_cart_url')) : ?>
                <a class="icon-button" href="<?php echo esc_url(wc_get_cart_url()); ?>" title="Warenkorb">
                    🛒
                </a>
            <?php endif; ?>
        </div>

    </div>
</header>
