<footer class="site-footer shop-site-footer"><div class="container">
  <div class="shop-footer-grid">
    <div><a class="brand" href="<?php echo esc_url(home_url('/')); ?>"><img class="cardyssey-real-logo" src="<?php echo esc_url(get_template_directory_uri().'/assets/cardyssey-emblem-gold.png'); ?>" alt="" width="42" height="42"><span>Cardyssey <small>SHOP</small></span></a><p>Trading Cards und Zubehör entdecken. Für Sammler gemacht.</p></div>
    <div><strong>Shop</strong><a href="<?php echo esc_url(cardyssey_shop_url()); ?>">Alle Produkte</a><a href="<?php echo esc_url(home_url('/#shop-kategorien')); ?>">Kategorien</a><?php if (function_exists('wc_get_cart_url')) : ?><a href="<?php echo esc_url(wc_get_cart_url()); ?>">Warenkorb</a><?php endif; ?></div>
    <div><strong>Cardyssey</strong><a href="https://cardyssey.de/">Zur Plattform</a><a href="https://cardyssey.de/#funktionen">Funktionen</a><a href="https://cardyssey.de/#ausblick">Coming Soon</a></div>
    <div><strong>Informationen</strong><?php foreach (['impressum'=>'Impressum','datenschutz'=>'Datenschutz','widerrufsbelehrung'=>'Widerruf','versand-und-zahlung'=>'Versand & Zahlung'] as $slug=>$label): $page=get_page_by_path($slug); if ($page) echo '<a href="'.esc_url(get_permalink($page)).'">'.esc_html($label).'</a>'; endforeach; ?></div>
  </div>
  <div class="shop-footer-bottom">© <?php echo date('Y'); ?> Cardyssey <span>SHOP / COLLECT / DISCOVER</span></div>
</div></footer>
<?php wp_footer(); ?></body></html>