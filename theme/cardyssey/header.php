<!doctype html>
<html <?php language_attributes(); ?>>
<head><meta charset="<?php bloginfo('charset'); ?>"><meta name="viewport" content="width=device-width, initial-scale=1"><?php wp_head(); ?></head>
<body <?php body_class(); ?>><?php wp_body_open(); ?>
<header class="site-header shop-site-header">
  <div class="container header-inner">
    <a class="brand" href="<?php echo esc_url(home_url('/')); ?>" aria-label="Cardyssey Shop Startseite">
      <img class="cardyssey-real-logo" src="<?php echo esc_url(get_template_directory_uri().'/assets/cardyssey-emblem-gold.png'); ?>" alt="" width="42" height="42"><span>Cardyssey <small>SHOP</small></span>
    </a>
    <nav class="main-nav" aria-label="Shop-Navigation">
      <a href="<?php echo esc_url(cardyssey_shop_url()); ?>">Alle Produkte</a>
      <a href="<?php echo esc_url(home_url('/#shop-kategorien')); ?>">Kategorien</a>
      <a href="https://cardyssey.de/">Die App ↗</a>
    </nav>
    <div class="header-actions">
      <?php if (function_exists('wc_get_page_id') && wc_get_page_id('myaccount')>0): ?><a class="shop-account-link" href="<?php echo esc_url(get_permalink(wc_get_page_id('myaccount'))); ?>"><?php echo is_user_logged_in() ? 'Mein Konto' : 'Anmelden'; ?></a><?php endif; ?>
      <?php if (function_exists('wc_get_cart_url')) : ?>
      <a class="shop-cart-link" href="<?php echo esc_url(wc_get_cart_url()); ?>" aria-label="Warenkorb">Warenkorb <?php if (function_exists('WC') && WC()->cart) echo '<span>'.(int)WC()->cart->get_cart_contents_count().'</span>'; ?></a>
      <?php endif; ?>
    </div>
  </div>
</header>