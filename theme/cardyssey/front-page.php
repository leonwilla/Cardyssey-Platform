<?php get_header(); ?>
<main class="shop-refresh">
  <section class="shop-hero">
    <div class="container shop-hero-layout">
      <div class="shop-hero-copy">
        <span class="shop-label">CARDYSSEY / TCG STORE</span>
        <h1>Für alles,<br><em>was du sammelst.</em></h1>
        <p>Trading Cards, versiegelte Produkte und Zubehör für dein Hobby. Entdecke das Sortiment im Cardyssey-Shop.</p>
        <div class="shop-hero-actions">
          <a class="shop-action" href="<?php echo esc_url(cardyssey_shop_url()); ?>">Produkte entdecken <span>↗</span></a>
          <a class="shop-action shop-action-secondary" href="https://cardyssey.de/">Die Cardyssey-App <span>↗</span></a>
        </div>
        <span class="shop-hero-foot">TRADING CARDS · ACCESSORIES · COLLECTING</span>
      </div>
      <div class="shop-hero-art" aria-label="Cardyssey Trading Card Store">
        <div class="shop-art-header"><span>DISCOVER YOUR NEXT CARD</span><span>01 / 03</span></div>
        <div class="shop-art-center">
          <div class="shop-art-card shop-art-card-one">TCG<br><strong>COLLECT.</strong></div>
          <div class="shop-art-card shop-art-card-two">CARDYSSEY<br><strong>DISCOVER.</strong></div>
          <div class="shop-art-card shop-art-card-three">STORE<br><strong>PLAY.</strong></div>
        </div>
        <div class="shop-art-caption">YOUR COLLECTION STARTS HERE</div>
      </div>
    </div>
  </section>
  <section class="container shop-discover" id="shop-kategorien">
    <div class="shop-section-title"><div><span class="shop-label">UNSER SORTIMENT</span><h2>Finde deinen nächsten Fund.</h2></div><a href="<?php echo esc_url(cardyssey_shop_url()); ?>">Alle Produkte ansehen ↗</a></div>
    <?php
    if (taxonomy_exists('product_cat')) {
      $categories = get_terms(['taxonomy'=>'product_cat','hide_empty'=>true,'number'=>6,'orderby'=>'count','order'=>'DESC','exclude'=>[get_option('default_product_cat')]]);
      if (!is_wp_error($categories) && !empty($categories)) {
        echo '<div class="shop-category-grid">';
        foreach ($categories as $category) {
          $thumbnail_id = get_term_meta($category->term_id, 'thumbnail_id', true);
          $src = $thumbnail_id ? wp_get_attachment_image_url($thumbnail_id,'medium') : '';
          echo '<a class="shop-category" href="'.esc_url(get_term_link($category)).'">';
          if ($src) echo '<img src="'.esc_url($src).'" alt="" loading="lazy">';
          echo '<span class="shop-category-content"><strong>'.esc_html($category->name).'</strong><small>'.(int)$category->count.' Produkte ↗</small></span></a>';
        }
        echo '</div>';
      } else {
        echo '<p class="shop-empty">Neue Kategorien werden ergänzt, sobald passende Produkte im Shop verfügbar sind.</p>';
      }
    }
    ?>
  </section>
  <section class="shop-products-block">
    <div class="container">
      <div class="shop-section-title"><div><span class="shop-label">NEU ENTDECKEN</span><h2>Aktuell im Shop</h2></div><a href="<?php echo esc_url(cardyssey_shop_url()); ?>">Zum Sortiment ↗</a></div>
      <?php
      if (class_exists('WooCommerce')) {
        $published = wp_count_posts('product');
        if ($published && !empty($published->publish)) {
          echo do_shortcode('[products limit="8" columns="4" orderby="date" order="DESC"]');
        } else {
          echo '<p class="shop-empty">Hier findest du unsere Produkte, sobald das Sortiment online ist.</p>';
        }
      } else echo '<p class="shop-empty">Das Sortiment wird vorbereitet.</p>';
      ?>
    </div>
  </section>
  <section class="container shop-app-banner" id="app"><div><span class="shop-label">MEHR ALS EIN SHOP</span><h2>Die Karten gekauft.<br><em>Die Sammlung im Blick.</em></h2><p>Mit der Cardyssey-App organisierst du deine Karten, verwaltest Sets und behältst verfügbare Marktwerte im Blick. Derzeit mit Fokus auf Pokémon – weitere TCGs sind geplant.</p></div><a class="shop-action" href="https://cardyssey.de/">Zur Cardyssey-Plattform ↗</a></section>
</main>
<?php get_footer(); ?>
