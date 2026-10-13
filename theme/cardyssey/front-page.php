<?php get_header(); ?>
<main class="freshShop">
  <section class="freshHero"><div class="container freshHeroGrid">
    <div class="freshIntro"><span class="freshEyebrow">CARDYSSEY — TRADING CARD STORE</span><h1>Gute Karten.<br><em>Gutes Gefühl.</em></h1><p>Entdecke Sammelkarten, Booster, Displays, Figuren, Plüschtiere und Zubehör – alles rund ums Sammeln. Ohne unnötige Umwege.</p><div class="freshButtons"><a class="freshPrimary" href="<?php echo esc_url(cardyssey_shop_url()); ?>">Zum Sortiment <span>↗</span></a><a class="freshSecondary" href="#welten">TCG-Welten entdecken ↓</a></div></div>
    <div class="freshHeroVisual"><div class="freshVisualHead">FÜR ALLE, DIE GERNE SAMMELN.</div><img class="freshHeroCardOne" src="<?php echo esc_url(get_template_directory_uri().'/assets/tcg-yugioh.jpg'); ?>" alt="Yu-Gi-Oh! Trading Card"><img class="freshHeroCardTwo" src="<?php echo esc_url(get_template_directory_uri().'/assets/tcg-pokemon.png'); ?>" alt="Pokémon Trading Card"><span class="freshVisualFoot">DISCOVER · COLLECT · ENJOY</span></div>
  </div></section>
  <section class="container freshBrowse" id="welten"><div class="freshSectionHeading"><div><span class="freshEyebrow">FÜR JEDES SAMMLERHERZ</span><h2>Deine TCG-Welt beginnt hier.</h2></div><p>Pokémon, Yu-Gi-Oh!, One Piece und Magic. Weitere Sammlerartikel findest du nach Produktart.</p></div>
   <div class="freshGames">
    <?php
    $worlds = ['Pokémon','Yu-Gi-Oh!','One Piece','Magic: The Gathering','Dragon Ball'];
    foreach ($worlds as $world) {
      $slug = sanitize_title($world);
      $existing = get_term_by('slug',$slug,'product_cat');
      $url = $existing && !is_wp_error($existing) && (int)$existing->count>0 ? get_term_link($existing) : '';
      if ($url && !is_wp_error($url)) {
        echo '<a class="freshGame" href="'.esc_url($url).'"><span>'.esc_html($world).'</span><small>Produkte ansehen ↗</small></a>';
      } else {
        echo '<div class="freshGame freshGameSoon"><span>'.esc_html($world).'</span><small>Sortiment folgt</small></div>';
      }
    }
    ?>
   </div>
  </section>
  <section class="container freshProductTypes" aria-labelledby="freshTypesTitle"><div class="freshSectionHeading"><div><span class="freshEyebrow">MEHR ALS KARTEN</span><h2 id="freshTypesTitle">Wonach suchst du?</h2></div><p>Vom einzelnen Kartenfund bis zum neuen Lieblingsstück für dein Regal.</p></div>
    <div class="freshTypeGrid"><?php
    $types = ['Einzelkarten','Booster & Packs','Displays & Boxen','Figuren & Sammlerstücke','Plüschtiere','Zubehör'];
    foreach($types as $type) {
      echo '<div class="freshTypeTile"><strong>'.esc_html($type).'</strong><span>Demnächst im Sortiment</span></div>';
    }
    ?></div>
  </section>
  <section class="freshCatalog"><div class="container"><div class="freshSectionHeading"><div><span class="freshEyebrow">SHOP THE COLLECTION</span><h2>Entdecke das Sortiment.</h2></div><a class="freshTextLink" href="<?php echo esc_url(cardyssey_shop_url()); ?>">Alle Artikel ↗</a></div>
    <?php
    if (class_exists('WooCommerce')) {
      $published = wp_count_posts('product');
      if ($published && !empty($published->publish)) echo do_shortcode('[products limit="8" columns="4" orderby="date" order="DESC"]');
      else echo '<div class="freshEmpty"><strong>Wir füllen gerade unsere Regale.</strong><p>Hier erscheinen unsere neuesten Produkte, sobald sie im Shop eingestellt sind. Bis dahin kannst du schon die TCG-Welten entdecken.</p><a href="https://cardyssey.de/">In der Cardyssey-App stöbern ↗</a></div>';
    }
    ?>
  </div></section>
  <section class="container freshServices"><div><span>GUT ZU WISSEN</span><h3>Ohne Konto shoppen.</h3><p>Du kannst als Gast bestellen oder ein Shop-Konto für deine Bestellungen nutzen.</p></div><div><span>FÜR DEIN HOBBY</span><h3>Mehr als nur Shop.</h3><p>Mit der Cardyssey-App organisierst du deine Sammlung und findest neue Karten.</p></div><div><span>IM AUFBAU</span><h3>Noch mehr geplant.</h3><p>Weitere TCGs, Shop-Funktionen und die Verknüpfung mit deinem Cardyssey-Konto folgen.</p></div></section>
  <section class="freshAppSection"><div class="container freshAppGrid"><div><span class="freshEyebrow">DIE CARDYSSEY-PLATTFORM</span><h2>Nach dem Auspacken<br>ist vor dem Sammeln.</h2><p>Scanne und verwalte deine Pokémon-Karten mit der Cardyssey-App. Neue Sammelkartenspiele sind in Planung.</p><a class="freshPrimary" href="https://cardyssey.de/">Cardyssey kennenlernen ↗</a></div><div class="freshAppFigure"><img src="<?php echo esc_url(get_template_directory_uri().'/assets/cardyssey-webapp-login.png'); ?>" alt="Originalaufnahme der Cardyssey-Webapp-Anmeldung"><span>Original-Webapp · Anmeldung</span></div></div></section>
</main>
<?php get_footer(); ?>